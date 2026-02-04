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


class SceneListItemWidget(QWidget):
    """Custom widget for a screenplay scene list item."""

    def __init__(self, title_text: str, summary_text: str, parent=None):
        super().__init__(parent)
        self._summary_full_text = summary_text or ""
        self._setup_ui(title_text)
        self.set_selected(False)

    def _setup_ui(self, title_text: str):
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(5, 0, 5, 0)
        outer_layout.setSpacing(0)

        self.card = QFrame(self)
        self.card.setObjectName("scene_item_card")
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        outer_layout.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        self.title_label = QLabel(title_text, self.card)
        self.title_label.setStyleSheet(
            "color: #f0f0f0; font-size: 13px; font-weight: 600;"
        )
        card_layout.addWidget(self.title_label)

        self.summary_label = QLabel(self._summary_full_text, self.card)
        self.summary_label.setStyleSheet("color: #c0c0c0; font-size: 11px;")
        self.summary_label.setWordWrap(False)
        self.summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card_layout.addWidget(self.summary_label)

        self._update_summary_elide()

    def set_selected(self, is_selected: bool):
        self._apply_card_style(is_selected)

    def set_summary_text(self, summary_text: str):
        self._summary_full_text = summary_text or ""
        self._update_summary_elide()

    def _apply_card_style(self, is_selected: bool):
        if is_selected:
            background_color = "#3f3f3f"
            border_color = "#5a9bd5"
        else:
            background_color = "#3a3a3a"
            border_color = "#2f2f2f"
        self.card.setStyleSheet(
            "QFrame#scene_item_card { background-color: %s; border: 1px solid %s; "
            "border-radius: 8px; }" % (background_color, border_color)
        )

    def _update_summary_elide(self):
        if not self.summary_label:
            return
        available_width = self.summary_label.width()
        if available_width <= 0:
            layout = self.card.layout()
            if layout:
                margins = layout.contentsMargins()
                available_width = self.card.width() - margins.left() - margins.right()
        if available_width <= 0:
            return
        metrics = self.summary_label.fontMetrics()
        elided = metrics.elidedText(
            self._summary_full_text, Qt.ElideRight, available_width
        )
        self.summary_label.setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_summary_elide()


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
        self.scene_list.setSpacing(5)
        # Set selection mode to single selection
        self.scene_list.setSelectionMode(QListWidget.SingleSelection)
        self.scene_list.itemClicked.connect(self._on_scene_selected)
        # Also connect itemDoubleClicked for double-click to edit
        self.scene_list.itemDoubleClicked.connect(self._on_scene_selected)
        self.scene_list.itemSelectionChanged.connect(self._update_scene_item_styles)
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
        self.scene_list.setUpdatesEnabled(False)
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
            self.scene_list.setUpdatesEnabled(True)
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

            overview_text = self._get_scene_overview(scene, display_num)
            item_widget = SceneListItemWidget(
                f"Scene {display_num}",
                overview_text,
                self.scene_list
            )
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.UserRole, scene.scene_id)
            self.scene_list.addItem(item)
            self.scene_list.setItemWidget(item, item_widget)

        self._update_scene_item_styles()
        self.scene_list.setUpdatesEnabled(True)
        logger.info(f"Scene list now has {self.scene_list.count()} items")

    def _update_scene_item_styles(self):
        """Update list item styling based on selection."""
        for index in range(self.scene_list.count()):
            item = self.scene_list.item(index)
            item_widget = self.scene_list.itemWidget(item)
            if isinstance(item_widget, SceneListItemWidget):
                item_widget.set_selected(item.isSelected())

    def _normalize_scene_text(self, text: Optional[str]) -> str:
        """Normalize scene text for display."""
        if not text:
            return ""
        return " ".join(text.strip().split())

    def _clean_summary_line(self, text: str) -> str:
        """Clean a summary line for display."""
        cleaned = text.strip()
        if cleaned.startswith("#"):
            cleaned = cleaned.lstrip("#").strip()
        if cleaned.startswith("**") and cleaned.endswith("**"):
            cleaned = cleaned.strip("*")
        if cleaned.startswith("_") and cleaned.endswith("_"):
            cleaned = cleaned.strip("_")
        return cleaned

    def _extract_content_summary(self, content: Optional[str]) -> str:
        """Extract a short summary from scene content."""
        if not content:
            return ""
        for line in content.splitlines():
            normalized = self._normalize_scene_text(line)
            if normalized:
                return self._clean_summary_line(normalized)
        return ""

    def _get_scene_overview(self, scene: ScreenPlayScene, display_num: str) -> str:
        """Get overview text for a scene."""
        logline = self._normalize_scene_text(scene.logline)
        if logline:
            return logline

        story_beat = self._normalize_scene_text(scene.story_beat)
        if story_beat:
            return story_beat

        title = self._normalize_scene_text(scene.title)
        expected_title = f"Scene {display_num}".lower()
        if title and title.lower() != expected_title:
            return title

        content_summary = self._extract_content_summary(scene.content)
        if content_summary:
            return content_summary

        if title:
            return title

        return "No overview available"
            
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