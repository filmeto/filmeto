"""Resources panel for managing project resources."""

from __future__ import annotations

import logging
import os
from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFileIconProvider,
    QHeaderView, QMenu, QTreeWidgetItemIterator, QWidget
)
from PySide6.QtCore import Qt, QSize, QFileInfo
from PySide6.QtGui import QIcon, QBrush, QColor

from app.ui.panels.base_panel import BasePanel
from app.data.workspace import Workspace
from app.workers.worker import BackgroundWorker, run_in_background
from utils.i18n_utils import tr
from .resource_preview import ResourcePreview

logger = logging.getLogger(__name__)


class ResourceTreeView(QTreeWidget):
    """Tree widget for displaying project resources."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_manager = None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the tree view UI."""
        # Set columns
        self.setHeaderLabels(["Name", "Type", "Size"])
        self.setHeaderHidden(False)
        
        # Configure header
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Set styling
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #2b2b2b;
                color: #bbbbbb;
                border: 1px solid #3c3f41;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #3c3f41;
            }
            QTreeWidget::item:selected {
                background-color: #3a75c9;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3f41;
                color: #bbbbbb;
                padding: 4px;
                border: 1px solid #2b2b2b;
            }
        """)
        
        # Set properties
        self.setIconSize(QSize(16, 16))
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        
        # Icon provider
        self.icon_provider = QFileIconProvider()
        
    def set_resources(self, resources, resource_manager):
        """Set the resources and update the tree view."""
        self.resource_manager = resource_manager
        self.refresh(resources)
        
    def refresh(self, resources=None):
        """Refresh the tree view with provided or current resources."""
        self.clear()
        
        if not self.resource_manager:
            return
            
        # Use provided resources or fetch all if not provided
        if resources is None:
            resources = self.resource_manager.get_all()
        
        if not resources:
            # Show empty state
            empty_item = QTreeWidgetItem(self)
            empty_item.setText(0, "No resources available")
            empty_item.setForeground(0, QBrush(QColor("#888888")))
            empty_item.setFlags(Qt.ItemIsEnabled)
            return
        
        # Group resources by media type
        resources_by_type = {}
        for resource in resources:
            media_type = resource.media_type
            if media_type not in resources_by_type:
                resources_by_type[media_type] = []
            resources_by_type[media_type].append(resource)
        
        # Create tree structure
        for media_type, type_resources in sorted(resources_by_type.items()):
            # Create category item
            category_item = QTreeWidgetItem(self)
            category_item.setText(0, f"{media_type}s ({len(type_resources)})")
            category_item.setText(1, "Folder")
            folder_icon = self.icon_provider.icon(QFileIconProvider.Folder)
            category_item.setIcon(0, folder_icon)
            category_item.setExpanded(True)
            
            # Add resources
            for resource in sorted(type_resources, key=lambda r: r.name):
                resource_item = QTreeWidgetItem(category_item)
                resource_item.setText(0, resource.name)
                resource_item.setText(1, media_type.capitalize())
                resource_item.setText(2, self._format_size(resource.file_size))
                resource_item.setToolTip(0, resource.get_absolute_path(
                    self.resource_manager.project_path))
                
                # Set icon based on file type
                # Use absolute path from resource to avoid macOS iconForFile: error
                resource_path = resource.get_absolute_path(self.resource_manager.project_path)
                file_info = QFileInfo(resource_path)
                icon = self.icon_provider.icon(file_info)
                resource_item.setIcon(0, icon)
                
                # Store resource data
                resource_item.setData(0, Qt.UserRole, resource)
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        return f"{size:.1f} {size_names[i]}"
    
    def filter_resources(self, filter_text):
        """Filter resources by name."""
        if not filter_text:
            # Show all items
            iterator = QTreeWidgetItemIterator(self)
            while iterator.value():
                item = iterator.value()
                item.setHidden(False)
                iterator += 1
            return
        
        filter_text = filter_text.lower()
        
        # Hide/show items based on filter
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if item.parent():  # Only filter leaf items
                name = item.text(0).lower()
                item.setHidden(filter_text not in name)
            iterator += 1
        
        # Hide empty categories
        for i in range(self.topLevelItemCount()):
            category = self.topLevelItem(i)
            has_visible_children = False
            for j in range(category.childCount()):
                if not category.child(j).isHidden():
                    has_visible_children = True
                    break
            category.setHidden(not has_visible_children)


class ResourcesPanel(BasePanel):
    """
    Panel for browsing and managing project resources.
    
    Provides tree view of resources, search/filter, preview, and operations.
    """
    
    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the resources panel."""
        self.resource_manager = None
        self._resources_load_worker: Optional[BackgroundWorker] = None
        super().__init__(workspace, parent)
    
    def setup_ui(self):
        """Set up the UI components."""
        self.set_panel_title(tr("Resource"))
        
        # Add refresh button to toolbar instead of search layout if we want it unified
        self.add_toolbar_button("↻", self._on_refresh_clicked, tr("刷新"))
        
        # Container for content
        content_container = QWidget()
        layout = QVBoxLayout(content_container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText(tr("搜索资源..."))
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #3c3f41;
                color: #bbbbbb;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #4a80b0;
            }
        """)
        self.search_box.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_box)
        
        layout.addLayout(search_layout)
        
        # Splitter for tree and preview
        splitter = QSplitter(Qt.Vertical, self)
        
        # Resource tree
        self.tree_view = ResourceTreeView(self)
        self.tree_view.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree_view)
        
        # Preview widget
        self.preview_widget = ResourcePreview(self)
        splitter.addWidget(self.preview_widget)
        
        # Set initial splitter sizes (70% tree, 30% preview)
        splitter.setSizes([350, 150])
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter, 1)
        
        # Info label at bottom
        self.info_label = QLabel("", self)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                padding: 2px;
            }
        """)
        layout.addWidget(self.info_label)
        
        self.content_layout.addWidget(content_container)
    
    def load_data(self):
        """Load resources data when panel is first activated."""
        super().load_data()
        self._load_resources()
        self._connect_signals()
    
    def on_activated(self):
        """Called when panel becomes visible."""
        super().on_activated()
        # Refresh resources when panel is activated (if data already loaded)
        if self._data_loaded:
            self._load_resources()
            self._connect_signals()
        logger.info("✅ Resources panel activated")
    
    def on_deactivated(self):
        """Called when panel is hidden."""
        super().on_deactivated()
        self._cancel_resources_load_worker()
        self._disconnect_signals()
        logger.info("⏸️ Resources panel deactivated")

    def _cancel_resources_load_worker(self) -> None:
        if self._resources_load_worker is not None:
            self._resources_load_worker.stop()
            self._resources_load_worker = None
    
    def _load_resources(self):
        """Load resources from the resource manager asynchronously."""
        try:
            # Get resource manager from project
            project = self.workspace.get_project()
            if not hasattr(project, 'get_resource_manager'):
                self.info_label.setText("Resource manager not available")
                return
            
            self.resource_manager = project.get_resource_manager()
            
            # Show loading state
            self.show_loading(tr("正在加载资源..."))
            self.info_label.setText(tr("正在加载资源..."))

            self._cancel_resources_load_worker()

            def _done(resources):
                self._resources_load_worker = None
                self._on_resources_loaded(resources)

            def _err(msg: str, exc):
                self._resources_load_worker = None
                ex = exc if isinstance(exc, Exception) else Exception(msg)
                self._on_load_error(msg, ex)

            self._resources_load_worker = run_in_background(
                self.resource_manager.get_all,
                on_finished=_done,
                on_error=_err,
                auto_cleanup=False,
                task_type="resources_panel_load",
            )
            
        except Exception as e:
            logger.error(f"❌ Error initiating resource load: {e}")
            self.info_label.setText(f"Error: {str(e)}")
            self.hide_loading()

    def _on_resources_loaded(self, resources):
        """Callback when resources are loaded from background thread"""
        if not self.resource_manager:
            self.hide_loading()
            return
            
        self.tree_view.set_resources(resources, self.resource_manager)
        
        # Update info
        resource_count = len(resources)
        self.info_label.setText(f"{resource_count} resource(s)")
        logger.info(f"✅ Resources panel UI updated with {resource_count} resources")
        self.hide_loading()

    def _on_load_error(self, error_msg: str, exception: Exception):
        """Handle loading error"""
        logger.error(f"❌ Error loading resources: {error_msg}")
        self.info_label.setText(f"Error: {error_msg}")
        self.hide_loading()
    
    def _connect_signals(self):
        """Connect to ResourceManager signals for auto-refresh."""
        if not self.resource_manager:
            return
        
        try:
            # Connect to resource manager signals
            self.resource_manager.resource_added.connect(self._on_resource_added)
            self.resource_manager.resource_updated.connect(self._on_resource_updated)
            self.resource_manager.resource_deleted.connect(self._on_resource_deleted)
            logger.info("✅ Connected to ResourceManager signals")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to ResourceManager signals: {e}")
    
    def _disconnect_signals(self):
        """Disconnect from ResourceManager signals."""
        if not self.resource_manager:
            return
        
        try:
            # Disconnect from resource manager signals
            self.resource_manager.resource_added.disconnect(self._on_resource_added)
            self.resource_manager.resource_updated.disconnect(self._on_resource_updated)
            self.resource_manager.resource_deleted.disconnect(self._on_resource_deleted)
            logger.info("✅ Disconnected from ResourceManager signals")
        except Exception as e:
            logger.warning(f"⚠️ Could not disconnect from ResourceManager signals: {e}")
    
    def _on_resource_added(self, resource):
        """Handle resource added signal."""
        logger.info(f"📥 Resource added: {resource.name}")
        self._load_resources()
    
    def _on_resource_updated(self, resource):
        """Handle resource updated signal."""
        logger.info(f"🔄 Resource updated: {resource.name}")
        self._load_resources()
    
    def _on_resource_deleted(self, resource_name):
        """Handle resource deleted signal."""
        logger.info(f"🗑️ Resource deleted: {resource_name}")
        self._load_resources()
        # Clear preview if deleted resource was selected
        self.preview_widget.clear_preview()
    
    def _on_search_changed(self, text):
        """Handle search text changes."""
        self.tree_view.filter_resources(text)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self._load_resources()
    
    def _on_selection_changed(self):
        """Handle tree selection changes."""
        selected_items = self.tree_view.selectedItems()
        if not selected_items:
            self.preview_widget.clear_preview()
            return
        
        item = selected_items[0]
        # Get resource from item data
        resource = item.data(0, Qt.UserRole)
        
        if resource:
            try:
                project = self.workspace.get_project()
                resource_manager = project.get_resource_manager()
                self.preview_widget.set_resource(resource, resource_manager.project_path)
            except Exception as e:
                logger.error(f"❌ Error showing preview: {e}")
