"""
Screen Play Panel

This module implements a panel for managing movie screenplay scenes with
support for adding, deleting, updating, and viewing scenes.
"""
import os
import logging
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QTextEdit, QLabel, QSplitter, QFrame, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

from app.ui.panels.base_panel import BasePanel
from app.data.screen_play import ScreenPlayManager, ScreenPlayScene

logger = logging.getLogger(__name__)


class ScreenPlayPanel(BasePanel):
    """Panel for managing screenplay scenes."""

    def __init__(self, workspace, parent=None):
        """Initialize the screen play panel."""
        # Initialize screenplay manager
        self.screenplay_manager = None
        self.current_project = None

        # Store current view state
        self.view_mode = "list"  # Either "list" or "editor"
        self.current_scene_id = None

        # Call parent constructor (will call setup_ui())
        super().__init__(workspace, parent)
        self.set_panel_title("Screen Play")

    def setup_ui(self):
        """Set up the UI components."""
        # Add refresh button to toolbar
        self.add_toolbar_button("\ue6b8", self._refresh_scenes, "Refresh Scenes")

        # Create splitter for list and editor
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("screenplay_splitter")
        # Set initial sizes for the splitter
        self.splitter.setSizes([400, 200])  # List gets more space initially
        # Ensure the splitter expands to fill available space
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create list view
        self._setup_list_view()

        # Create editor view (initially hidden)
        self._setup_editor_view()

        # Add splitter to content layout (already created by BasePanel)
        self.content_layout.addWidget(self.splitter)

        # Initially show list view
        self._show_list_view()
        
    def _setup_list_view(self):
        """Set up the scene list view."""
        # Container for list view
        self.list_container = QWidget()
        self.list_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Toolbar for list view
        self.list_toolbar = self._create_toolbar()
        list_layout.addWidget(self.list_toolbar)

        # Scene list
        self.scene_list = QListWidget()
        self.scene_list.setObjectName("screenplay_scene_list")
        self.scene_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set selection mode to single selection
        self.scene_list.setSelectionMode(QListWidget.SingleSelection)
        self.scene_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                alternate-background-color: #3a3a3a;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #4a4a4a;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
        """)
        self.scene_list.itemClicked.connect(self._on_scene_selected)
        # Also connect itemDoubleClicked for double-click to edit
        self.scene_list.itemDoubleClicked.connect(self._on_scene_selected)
        list_layout.addWidget(self.scene_list)

        # Add to splitter
        self.splitter.addWidget(self.list_container)
        
    def _setup_editor_view(self):
        """Set up the scene editor view."""
        # Container for editor view
        self.editor_container = QWidget()
        self.editor_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # Toolbar for editor view
        self.editor_toolbar = self._create_editor_toolbar()
        editor_layout.addWidget(self.editor_toolbar)

        # Editor for screenplay content
        self.editor = QTextEdit()
        self.editor.setObjectName("screenplay_editor")
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        editor_layout.addWidget(self.editor)

        # Add to splitter
        self.splitter.addWidget(self.editor_container)

        # Hide initially
        self.editor_container.hide()

    def _create_icon_button(self, icon_code, tooltip, callback):
        """Create an icon button with iconfont icon and tooltip."""
        button = QPushButton(icon_code)
        button.setFixedSize(32, 32)
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #A0A0A0;
                font-family: "iconfont";
                font-size: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #4D4D4D;
            }
        """)
        button.setToolTip(tooltip)
        button.setCursor(QCursor(Qt.PointingHandCursor))
        if callback:
            button.clicked.connect(callback)
        return button

    def _create_toolbar(self):
        """Create toolbar for list view."""
        toolbar = QFrame()
        toolbar.setObjectName("screenplay_toolbar")
        toolbar.setStyleSheet("""
            QFrame#screenplay_toolbar {
                background-color: #2D2D2D;
                border-bottom: 1px solid #1E1E1E;
                padding: 5px;
            }
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Add scene button
        self.add_scene_btn = self._create_icon_button("\ue835", "Add Scene", self._add_scene)
        layout.addWidget(self.add_scene_btn)

        # Refresh button
        self.refresh_btn = self._create_icon_button("\ue6b8", "Refresh", self._refresh_scenes)
        layout.addWidget(self.refresh_btn)

        # Stretch to push other buttons to the left
        layout.addStretch()

        return toolbar

    def _create_editor_toolbar(self):
        """Create toolbar for editor view."""
        toolbar = QFrame()
        toolbar.setObjectName("screenplay_editor_toolbar")
        toolbar.setStyleSheet("""
            QFrame#screenplay_editor_toolbar {
                background-color: #2D2D2D;
                border-bottom: 1px solid #1E1E1E;
                padding: 5px;
            }
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Return to list button
        self.return_btn = self._create_icon_button("\ue64f", "Return to List", self._return_to_list)
        layout.addWidget(self.return_btn)

        # Save button
        self.save_btn = self._create_icon_button("\ue654", "Save Scene", self._save_scene)
        layout.addWidget(self.save_btn)

        # Add screenplay formatting buttons
        self.action_btn = self._create_icon_button("\ue702", "Action", self._insert_action_format)
        layout.addWidget(self.action_btn)

        self.character_btn = self._create_icon_button("\ue60c", "Character", self._insert_character_format)
        layout.addWidget(self.character_btn)

        self.dialog_btn = self._create_icon_button("\ue721", "Dialogue", self._insert_dialogue_format)
        layout.addWidget(self.dialog_btn)

        # Stretch to push other buttons to the left
        layout.addStretch()

        return toolbar
        
    def _add_scene(self):
        """Add a new scene to the screenplay."""
        if not self.screenplay_manager:
            return
            
        # Generate a unique scene ID
        import uuid
        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        
        # Create a new scene with default content
        new_scene = ScreenPlayScene(
            scene_id=scene_id,
            title=f"Scene {len(self.screenplay_manager.list_scenes()) + 1}",
            content="# INT. LOCATION - DAY\n\nACTION DESCRIPTION HERE.\n\nCHARACTER NAME\nWhat the character says here.\n\n_CUT TO:_",
            scene_number=str(len(self.screenplay_manager.list_scenes()) + 1)
        )
        
        # Save the scene
        success = self.screenplay_manager.create_scene(
            scene_id=new_scene.scene_id,
            title=new_scene.title,
            content=new_scene.content,
            metadata=new_scene.to_dict()
        )
        
        if success:
            self._refresh_scenes()
        
    def _refresh_scenes(self):
        """Refresh the scene list."""
        if not self.screenplay_manager:
            return

        # Clear the current list
        self.scene_list.clear()

        # Get all scenes
        scenes = self.screenplay_manager.list_scenes()

        logger.info(f"Loading {len(scenes)} scenes from screenplay manager")
        logger.info(f"Screenplay manager screen_plays_dir: {self.screenplay_manager.screen_plays_dir}")

        if not scenes:
            # Show empty state message
            empty_item = QListWidgetItem("No scenes found. Click 'Add Scene' to create one.")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make non-selectable
            self.scene_list.addItem(empty_item)
            logger.info("No scenes found - showing empty state")
            return

        # Sort scenes by scene_number
        def get_scene_sort_key(scene):
            """Get sort key for a scene."""
            try:
                # Try to parse scene_number as integer for proper numeric sorting
                return int(scene.scene_number)
            except (ValueError, TypeError):
                # If scene_number is not numeric, use string comparison
                return scene.scene_number

        scenes.sort(key=get_scene_sort_key)

        # Add each scene to the list
        for scene in scenes:
            item = QListWidgetItem()
            # Convert scene_number to int for cleaner display if it's numeric
            scene_num = scene.scene_number
            try:
                scene_num_int = int(scene_num)
                display_num = str(scene_num_int)
            except (ValueError, TypeError):
                display_num = scene_num

            item.setText(f"Scene {display_num}: {scene.title}")
            item.setData(Qt.UserRole, scene.scene_id)
            self.scene_list.addItem(item)

        logger.info(f"Scene list now has {self.scene_list.count()} items")
            
    def _on_scene_selected(self, item):
        """Handle scene selection."""
        scene_id = item.data(Qt.UserRole)
        if scene_id:
            self._show_scene_editor(scene_id)
            
    def _show_scene_editor(self, scene_id):
        """Show the scene editor for the selected scene."""
        if not self.screenplay_manager:
            return
            
        # Get the scene
        scene = self.screenplay_manager.get_scene(scene_id)
        if not scene:
            return
            
        # Store current scene ID
        self.current_scene_id = scene_id
        
        # Set the editor content
        self.editor.setPlainText(scene.content)
        
        # Switch to editor view
        self._show_editor_view()
        
    def _show_list_view(self):
        """Show the list view."""
        self.list_container.show()
        self.editor_container.hide()
        self.view_mode = "list"
        
    def _show_editor_view(self):
        """Show the editor view."""
        self.list_container.hide()
        self.editor_container.show()
        self.view_mode = "editor"
        
    def _return_to_list(self):
        """Return to the list view."""
        self._show_list_view()
        self.current_scene_id = None
        
    def _save_scene(self):
        """Save the current scene."""
        if not self.screenplay_manager or not self.current_scene_id:
            return
            
        # Get the updated content from the editor
        updated_content = self.editor.toPlainText()
        
        # Update the scene
        success = self.screenplay_manager.update_scene(
            scene_id=self.current_scene_id,
            content=updated_content
        )
        
        if success:
            # Optionally show a success message
            pass
            
    def _insert_action_format(self):
        """Insert action format at cursor position."""
        cursor = self.editor.textCursor()
        cursor.insertText("\nACTION DESCRIPTION GOES HERE.\n")
        
    def _insert_character_format(self):
        """Insert character format at cursor position."""
        cursor = self.editor.textCursor()
        cursor.insertText("\nCHARACTER_NAME\n")
        
    def _insert_dialogue_format(self):
        """Insert dialogue format at cursor position."""
        cursor = self.editor.textCursor()
        cursor.insertText("\nWhat the character says here.\n")
        
    def load_data(self):
        """Load screenplay data for the current project."""
        # Get the current project
        project = self.workspace.get_project()
        if not project:
            # If no project is available, clear the scene list
            if hasattr(self, 'scene_list') and self.scene_list:
                self.scene_list.clear()
            return

        # Initialize screenplay manager for the project
        try:
            self.screenplay_manager = project.get_screenplay_manager()
            self.current_project = project

            # Load scenes
            self._refresh_scenes()
        except AttributeError as e:
            # If the project doesn't have a screenplay manager yet, create one
            from app.data.screen_play import ScreenPlayManager
            # Use project_path directly - ScreenPlayManager will create screen_plays subdirectory
            self.screenplay_manager = ScreenPlayManager(project.project_path)
            self.current_project = project

            # Load scenes
            self._refresh_scenes()
        except Exception as e:
            # Log any other errors during loading
            logger.error(f"Error loading screenplay data: {e}", exc_info=True)

    def on_project_switched(self, project_name: str):
        """Called when the project is switched."""
        super().on_project_switched(project_name)
        # Reload data for the new project
        self.load_data()

    def on_activated(self):
        """Called when the panel becomes visible."""
        super().on_activated()
        # Ensure data is loaded when panel is activated
        # The BasePanel.on_activated will call load_data via QTimer if needed
        # But also call it directly here for immediate refresh when switching panels

        # Ensure proper layout
        self.adjustSize()
        if self.parent():
            self.parent().adjustSize()

        logger.info(f"ScreenPlayPanel activated, screenplay_manager={self.screenplay_manager is not None}")

        # Also refresh the scene list if we have a manager
        if self.screenplay_manager:
            self._refresh_scenes()