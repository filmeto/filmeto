# -*- coding: utf-8 -*-
"""
Project List Widget for Startup Mode

This widget displays a list of projects in the left panel of the startup mode.
It includes a logo at the top, project list in the middle, and a toolbar at the bottom.
"""
import logging
import uuid

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QLineEdit, QDialog,
    QDialogButtonBox, QListWidget, QListWidgetItem, QSplitter,
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath, QPen

from app.data.project import scan_valid_project_names
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.core.base_worker import FunctionWorker
from app.ui.core.task_manager import TaskManager
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ProjectItemWidget(QFrame):
    """Widget representing a single project item in the list."""
    
    clicked = Signal(str)  # Emits project name when clicked
    edit_clicked = Signal(str)  # Emits project name when edit button clicked
    
    def __init__(self, project_name: str, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self._is_selected = is_selected
        
        self.setObjectName("project_item")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Project icon (first letter)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self._create_icon()
        layout.addWidget(self.icon_label)
        
        # Project name
        self.name_label = QLabel(project_name)
        self.name_label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
        layout.addWidget(self.name_label, 1)
        
        # Edit button (only visible on hover or when selected)
        self.edit_button = QPushButton("\ue601")  # Edit icon
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setVisible(False)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888888;
                font-family: iconfont;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #4080ff;
            }
        """)
        layout.addWidget(self.edit_button)
        
        self._update_style()
    
    def _create_icon(self):
        """Create a rounded letter icon for the project."""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background circle
        bg_color = QColor("#4080ff")
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw letter
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Sans-serif", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignCenter, self.project_name[0].upper())
        
        painter.end()
        self.icon_label.setPixmap(pixmap)
    
    def _update_style(self):
        """Update widget style based on selection state."""
        if self._is_selected:
            self.setStyleSheet("""
                QFrame#project_item {
                    background-color: rgba(61, 79, 124, 0.6);
                    border-radius: 6px;
                    border: 1px solid #4080ff;
                }
            """)
            self.edit_button.setVisible(True)
        else:
            self.setStyleSheet("""
                QFrame#project_item {
                    background-color: transparent;
                    border-radius: 6px;
                    border: 1px solid transparent;
                }
                QFrame#project_item:hover {
                    background-color: rgba(60, 63, 65, 0.5);
                }
            """)
    
    def set_selected(self, selected: bool):
        """Set the selection state."""
        self._is_selected = selected
        self._update_style()
        self.edit_button.setVisible(selected)
    
    def enterEvent(self, event):
        """Show edit button on hover."""
        if not self._is_selected:
            self.edit_button.setVisible(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide edit button when not hovered (unless selected)."""
        if not self._is_selected:
            self.edit_button.setVisible(False)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press to select project."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.project_name)
        super().mousePressEvent(event)
    
    def _on_edit_clicked(self):
        """Handle edit button click."""
        self.edit_clicked.emit(self.project_name)


class ProjectListWidget(BaseWidget):
    """Widget for displaying the project list in the startup left panel."""
    
    project_selected = Signal(str)  # Emits project name when selected
    project_edit = Signal(str)  # Emits project name when edit is requested
    project_created = Signal(str)  # Emits project name when a new project is created
    projects_reload = Signal()  # Emitted after list UI + ProjectManager are in sync

    def __init__(self, workspace: Workspace, parent=None, defer_projects_load: bool = False):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)
        
        self.setObjectName("project_list_widget")
        # Width will be controlled by parent container, don't set fixed width
        
        self._selected_project = None
        self._project_items = {}
        self._project_scan_generation = 0

        self._setup_ui()
        if not defer_projects_load:
            self._load_projects()
        self._apply_styles()
    
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top: branding / header (fixed height)
        header = QWidget()
        header.setObjectName("project_list_header")
        header.setFixedHeight(80)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(12)

        logo_label = QLabel()
        logo_label.setFixedSize(40, 40)
        logo_label.setPixmap(self._create_logo_pixmap())
        header_layout.addWidget(logo_label)

        app_name = QLabel("Filmeto")
        app_name.setStyleSheet("color: #E1E1E1; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(app_name)
        header_layout.addStretch()

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(60, 63, 65, 0.5);")
        separator.setFixedHeight(1)

        top_section = QWidget()
        top_section.setObjectName("project_list_top_section")
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(header)
        top_layout.addWidget(separator)
        top_section.setFixedHeight(81)

        # Middle: scrollable project list (takes remaining height)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("project_list_scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea::viewport {
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        self.project_list_container = QWidget()
        self.project_list_container.setStyleSheet("background-color: transparent;")
        self.project_list_layout = QVBoxLayout(self.project_list_container)
        self.project_list_layout.setContentsMargins(8, 8, 8, 8)
        self.project_list_layout.setSpacing(4)
        self.project_list_layout.setAlignment(Qt.AlignTop)
        self.project_list_layout.addStretch()

        scroll_area.setWidget(self.project_list_container)

        # Bottom: toolbar (fixed height)
        toolbar = QWidget()
        toolbar.setObjectName("project_list_toolbar")
        toolbar.setFixedHeight(56)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(8)

        self.add_button = QPushButton("\ue6b3")  # Add icon
        self.add_button.setToolTip(tr("新建项目"))
        self.add_button.setFixedSize(40, 40)
        self.add_button.clicked.connect(self._on_add_project)
        toolbar_layout.addWidget(self.add_button)

        toolbar_layout.addStretch()

        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("project_list_splitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(top_section)
        splitter.addWidget(scroll_area)
        splitter.addWidget(toolbar)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        layout.addWidget(splitter, 1)
    
    def _create_logo_pixmap(self) -> QPixmap:
        """Placeholder pixmap when no application icon is applied (dashed frame)."""
        size = 40
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor("#6a6d70"))
        pen.setStyle(Qt.DashLine)
        pen.setWidthF(1.25)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        margin = 2.5
        painter.drawRoundedRect(
            QRectF(margin, margin, size - 2 * margin, size - 2 * margin),
            6.0,
            6.0,
        )

        painter.end()
        return pixmap
    
    def _apply_styles(self):
        """Apply styles to the widget."""
        self.setStyleSheet("""
            QWidget#project_list_widget {
                background-color: transparent;
            }
            QWidget#project_list_header {
                background-color: transparent;
            }
            QWidget#project_list_toolbar {
                background-color: transparent;
                border-top: 1px solid rgba(60, 63, 65, 0.5);
            }
            QSplitter#project_list_splitter::handle {
                background-color: rgba(60, 63, 65, 0.35);
            }
            QPushButton {
                background-color: rgba(60, 63, 65, 0.6);
                border: none;
                border-radius: 6px;
                color: #E1E1E1;
                font-family: iconfont;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: rgba(76, 80, 82, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(44, 47, 49, 0.8);
            }
        """)
    
    def _load_projects(self):
        """Load projects from the workspace (blocking scan + build on GUI thread)."""
        self.workspace.project_manager.ensure_projects_loaded()
        self._rebuild_project_list_ui()

    def _rebuild_project_list_ui(self):
        """Rebuild list widgets from ``project_manager.projects`` (GUI thread)."""
        project_names = sorted(self.workspace.project_manager.projects.keys())

        while self.project_list_layout.count() > 1:
            item = self.project_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._project_items.clear()

        for name in project_names:
            self._add_project_item(name)

        if project_names:
            self._select_project(project_names[0])
        self.projects_reload.emit()
    
    def _add_project_item(self, project_name: str):
        """Add a project item to the list."""
        item = ProjectItemWidget(project_name)
        item.clicked.connect(self._select_project)
        item.edit_clicked.connect(self._on_project_edit)
        
        # Insert before the stretch (which is always the last item)
        # Get the index of the last item (stretch) and insert before it
        stretch_index = self.project_list_layout.count() - 1
        self.project_list_layout.insertWidget(stretch_index, item)
        self._project_items[project_name] = item
    
    def _select_project(self, project_name: str):
        """Select a project in the list."""
        # Deselect previous
        if self._selected_project and self._selected_project in self._project_items:
            self._project_items[self._selected_project].set_selected(False)
        
        # Select new
        self._selected_project = project_name
        if project_name in self._project_items:
            self._project_items[project_name].set_selected(True)
        
        self.project_selected.emit(project_name)
    
    def _on_project_edit(self, project_name: str):
        """Handle project edit request."""
        self.project_edit.emit(project_name)
    
    def _on_add_project(self):
        """Handle add project button click."""
        from app.ui.dialog.custom_dialog import CustomDialog
        
        dialog = CustomDialog(self)
        dialog.set_title(tr("新建项目"))
        
        # Create content layout
        content_layout = QVBoxLayout()
        
        # Label
        label = QLabel(tr("请输入项目名称:"))
        label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
        content_layout.addWidget(label)
        
        # Input field
        line_edit = QLineEdit()
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 8px;
                color: #E1E1E1;
                selection-background-color: #4080ff;
                font-size: 14px;
            }
        """)
        content_layout.addWidget(line_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            dialog
        )
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #3d3f4e;
                color: #E1E1E1;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 6px 15px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #444654;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        content_layout.addWidget(button_box)
        
        dialog.setContentLayout(content_layout)
        line_edit.setFocus()
        
        if dialog.exec() == QDialog.Accepted:
            project_name = line_edit.text().strip()
            if project_name:
                try:
                    self.workspace.project_manager.create_project(project_name)
                    self._add_project_item(project_name)
                    self._select_project(project_name)
                    self.project_created.emit(project_name)
                except Exception as e:
                    logger.error(f"Error creating project: {e}")
    
    def get_selected_project(self) -> str:
        """Get the currently selected project name."""
        return self._selected_project
    
    def refresh(self):
        """Scan projects off the UI thread, then build Project + list on GUI thread."""
        pm = self.workspace.project_manager
        self._project_scan_generation += 1
        gen = self._project_scan_generation
        worker = FunctionWorker(
            scan_valid_project_names,
            pm.projects_dir,
            task_id=f"project-scan-{id(self)}-{gen}-{uuid.uuid4().hex[:8]}",
            task_type="project_scan",
        )
        worker.signals.finished.connect(
            lambda tid, res, g=gen: self._on_project_scan_finished(tid, res, g)
        )
        worker.signals.error.connect(
            lambda tid, msg, exc, g=gen: self._on_project_scan_error(tid, msg, exc, g)
        )
        TaskManager.instance().submit(worker)

    def _on_project_scan_finished(self, task_id: str, names: object, gen: int) -> None:
        if gen != self._project_scan_generation:
            return
        name_list = names if isinstance(names, list) else []
        try:
            self.workspace.project_manager.replace_projects_from_names(name_list)
            self._rebuild_project_list_ui()
        except Exception as e:
            logger.error("Failed to apply project scan: %s", e, exc_info=True)
            self._load_projects()

    def _on_project_scan_error(
        self, task_id: str, msg: str, exc: object, gen: int
    ) -> None:
        if gen != self._project_scan_generation:
            return
        logger.error("Project scan task failed: %s", msg, exc_info=exc)
        self._load_projects()
