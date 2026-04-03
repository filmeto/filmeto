# task_list_widget.py
from __future__ import annotations

import json
import yaml
import logging
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, Slot, QRect
from .enhanced_task_item_widget import EnhancedTaskItemWidget
import os

from ..base_widget import BaseWidget, BaseTaskWidget
from app.ui.workers.background_worker import BackgroundWorker, run_in_background
from utils.i18n_utils import tr, translation_manager

logger = logging.getLogger(__name__)


class TaskListWidget(BaseTaskWidget):
    task_action_signal = Signal(str, str)  # action, task_id

    def __init__(self, parent, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self._current_timeline_item = None
        self.task_manager = None  # Will be set based on current timeline item
        self.loaded_tasks = {}  # task_id -> widget
        self.all_task_dirs = []
        self.current_index = 0
        self.page_size = 10
        self.loading = False
        self.selected_task_widget = None  # Track the currently selected task widget
        self._tasks_refresh_worker: Optional[BackgroundWorker] = None
        self._load_more_worker: Optional[BackgroundWorker] = None

        # Connect to workspace task progress updates instead of using file system monitoring
        self.workspace.connect_task_progress(self.on_task_progress_update)
        self.init_ui()
        
        # Initialize with current timeline item's tasks
        self._update_task_manager_for_current_item()
        # Initial load of tasks - only populate the UI with tasks already loaded in task_manager
        self.populate_initial_tasks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # No margins for full width usage

        # 设置背景色匹配右栏
        self.setStyleSheet("background-color: #292b2e;")
        
        # Set fixed width
        self.setFixedWidth(200)
        
        # Set size policy and fixed width
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(200)

        # 刷新按钮
        top_layout = QHBoxLayout()
        self.refresh_btn = QPushButton(tr("🔄 刷新任务"))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3f4e;
                color: #E1E1E1;
                border: 1px solid #505254;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #717171;
            }
        """)
        # Adjust button size for new width
        self.refresh_btn.setFixedHeight(30)
        self.refresh_btn.clicked.connect(self.refresh_tasks)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # 设置滚动区域样式 - hide scrollbars
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #1e1f22;
                background-color: #292b2e;
            }
            QScrollBar:vertical { 
                width: 0px;
            }
            QScrollBar:horizontal { 
                height: 0px;
            }
        """)
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #292b2e;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(5)  # Add spacing between items
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)  # Add margins to scroll layout
        self.scroll_area.setWidget(self.scroll_content)

        layout.addWidget(self.scroll_area)

        # 滚动到底部加载更多
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.check_scroll)
        
        # Connect to language change signal
        translation_manager.language_changed.connect(self.retranslateUi)

    def retranslateUi(self):
        """更新所有UI文本当语言变化时"""
        self.refresh_btn.setText(tr("🔄 刷新任务"))

    def _update_task_manager_for_current_item(self):
        """Update the task manager reference based on current timeline item"""
        current_item = self.workspace.get_current_timeline_item()
        if current_item:
            self._current_timeline_item = current_item
            self.task_manager = current_item.get_task_manager()
        else:
            self._current_timeline_item = None
            self.task_manager = None

    def on_timeline_switch(self, item):
        """Handle timeline item switch - reload tasks for the new item"""
        if item != self._current_timeline_item:
            self._cancel_task_list_workers()
            self._current_timeline_item = item
            if item:
                self.task_manager = item.get_task_manager()
            else:
                self.task_manager = None
            # Refresh to show tasks for the new timeline item
            self.refresh_tasks()
    
    def on_task_create(self, task):
        self.refresh_tasks()

    def load_all_task_dirs(self):
        # Get all task directories from TaskManager
        try:
            if self.task_manager is None:
                self.all_task_dirs = []
                return
            all_task_ids = sorted([task_id for task_id in self.task_manager.tasks.keys() if task_id.isdigit()], 
                                 key=lambda x: int(x), reverse=True)
            self.all_task_dirs = all_task_ids
        except Exception as e:
            logger.error(f"读取任务目录失败: {e}")
            self.all_task_dirs = []

    def on_task_item_clicked(self, task_widget):
        """Handle task item click events"""
        # Deselect the previously selected widget if it exists and is different
        if self.selected_task_widget and self.selected_task_widget != task_widget:
            self.selected_task_widget.set_selected(False)
        
        # Toggle the selection state of the clicked widget
        if self.selected_task_widget == task_widget:
            # Clicking the already selected item deselects it
            task_widget.set_selected(False)
            self.selected_task_widget = None
        else:
            # Select the new widget
            task_widget.set_selected(True)
            self.selected_task_widget = task_widget
        
        # Show/hide preview panel as needed
        if self.selected_task_widget:
            self.show_preview_panel()
        else:
            self.hide_preview_panel()

    def show_preview_panel(self):
        """Show the preview panel for the selected task"""
        # Create the preview panel if it doesn't exist
        if not hasattr(self, 'preview_panel'):
            from .task_item_preview_widget import TaskItemPreviewWidget
            self.preview_panel = TaskItemPreviewWidget()
            # Install event filter to handle clicks outside task items
            from PySide6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self)
        
        # Set the task to preview
        if self.selected_task_widget and self.selected_task_widget.task:
            self.preview_panel.set_task(self.selected_task_widget.task)
            # Adjust size after content is loaded
            self.preview_panel.adjustSize()
        
        # Position the preview panel to the left of the selected task item
        # Align the top edge of the preview panel with the top edge of the task item
        if self.selected_task_widget:
            item_pos = self.selected_task_widget.mapToGlobal(self.selected_task_widget.rect().topLeft())
            # Position to the left of the task list, aligned with item top
            task_list_pos = self.mapToGlobal(self.rect().topLeft())
            preview_size = self.preview_panel.size()
            preview_x = task_list_pos.x() - preview_size.width() - 10  # 10px spacing
            preview_y = item_pos.y()
            self.preview_panel.setGeometry(preview_x, preview_y, preview_size.width(), preview_size.height())
        
        # Show the preview panel
        self.preview_panel.show()

    def hide_preview_panel(self):
        """Hide the preview panel"""
        if hasattr(self, 'preview_panel'):
            self.preview_panel.hide()
    
    def eventFilter(self, obj, event):
        """Event filter to handle clicks outside task items"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        
        # Handle mouse press events
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent):
                # Check if the click is outside the task list widget and preview panel
                click_pos = event.globalPos()
                
                # Check if click is on preview panel (don't close if clicking on preview)
                if hasattr(self, 'preview_panel') and self.preview_panel.isVisible():
                    preview_rect = self.preview_panel.geometry()
                    if preview_rect.contains(click_pos):
                        return False  # Let the event propagate normally
                
                # Check if click is on any task item
                clicked_on_item = False
                for widget in self.loaded_tasks.values():
                    if widget.isVisible():
                        # Get the widget's geometry in global coordinates
                        widget_top_left = widget.mapToGlobal(widget.rect().topLeft())
                        widget_rect = QRect(widget_top_left, widget.rect().size())
                        if widget_rect.contains(click_pos):
                            clicked_on_item = True
                            break
                
                # Check if click is on the task list widget itself (but not on items)
                task_list_top_left = self.mapToGlobal(self.rect().topLeft())
                task_list_rect = QRect(task_list_top_left, self.rect().size())
                clicked_on_task_list = task_list_rect.contains(click_pos)
                
                # If click is outside both task items and preview panel and task list, hide preview
                if not clicked_on_item and not clicked_on_task_list and hasattr(self, 'preview_panel') and self.preview_panel.isVisible():
                    self.hide_preview_panel()
                    if self.selected_task_widget:
                        self.selected_task_widget.set_selected(False)
                        self.selected_task_widget = None
        
        return False  # Let other events propagate normally

    def _cancel_task_list_workers(self):
        for w in (self._tasks_refresh_worker, self._load_more_worker):
            if w is not None:
                w.stop()
        self._tasks_refresh_worker = None
        self._load_more_worker = None

    def _apply_loaded_task_page(self, _loaded: list):
        """After disk load, ``task_manager.tasks`` is filled on the GUI thread; append one UI page."""
        all_task_ids = sorted(
            [task_id for task_id in self.task_manager.tasks.keys() if task_id.isdigit()],
            key=lambda x: int(x),
            reverse=True,
        )
        self.all_task_dirs = all_task_ids
        page = self.task_manager.get_all_tasks(self.current_index, self.page_size)
        self.on_tasks_loaded(page)

    def load_more_tasks(self):
        if self.loading:
            return
        if self.task_manager is None:
            return

        if self.task_manager.tasks:
            self.loading = True
            try:
                tasks = self.task_manager.get_all_tasks(self.current_index, self.page_size)
                all_task_ids = sorted(
                    [task_id for task_id in self.task_manager.tasks.keys() if task_id.isdigit()],
                    key=lambda x: int(x),
                    reverse=True,
                )
                self.all_task_dirs = all_task_ids
                self.on_tasks_loaded(tasks)
            except Exception as e:
                logger.error(f"加载任务失败: {e}")
                self.loading = False
            return

        self.loading = True
        tm = self.task_manager

        def fetch():
            return tm.load_all_tasks_thread_worker()

        def on_finished(loaded):
            self._load_more_worker = None
            try:
                tm.tasks.clear()
                for t in loaded:
                    tm.tasks[t.task_id] = t
                self._apply_loaded_task_page(loaded)
            except Exception as e:
                logger.error(f"加载任务失败: {e}")
                self.loading = False

        def on_error(msg: str, _exc: Exception):
            self._load_more_worker = None
            logger.error(f"加载任务失败: {msg}")
            self.loading = False

        self._load_more_worker = run_in_background(
            fetch,
            on_finished=on_finished,
            on_error=on_error,
            auto_cleanup=False,
            task_type="task_list_load_more",
        )

    @Slot(list)
    def on_tasks_loaded(self, tasks):
        for task in tasks:
            if task.task_id in self.loaded_tasks:
                # 更新已有任务
                widget = self.loaded_tasks[task.task_id]
                widget.update_display(task)
                continue
            widget = EnhancedTaskItemWidget(task, self.workspace)
            widget.clicked.connect(self.on_task_item_clicked)
            self.scroll_layout.addWidget(widget)
            self.loaded_tasks[task.task_id] = widget
        self.current_index += self.page_size
        self.loading = False

    def check_scroll(self, value):
        scrollbar = self.scroll_area.verticalScrollBar()
        if value >= scrollbar.maximum() - 20:  # 阈值
            self.load_more_tasks()

    def on_task_action(self):
        sender = self.sender()
        if hasattr(sender, 'task_id'):
            task_id = sender.task_id
            # 这里可以根据 sender 类型判断 action
            # 为简化，我们统一处理
            pass
    
    def populate_initial_tasks(self):
        """使用已经加载到task_manager中的任务来初始化UI"""
        if self.task_manager is None:
            return
            
        # 获取已经加载的任务
        tasks = list(self.task_manager.tasks.values())
        # 按ID降序排列（最新的在前）
        tasks.sort(key=lambda t: int(t.task_id), reverse=True)
        
        # 只加载第一页的任务
        initial_tasks = tasks[:self.page_size]
        for task in initial_tasks:
            widget = EnhancedTaskItemWidget(task, self.workspace)
            widget.clicked.connect(self.on_task_item_clicked)
            self.scroll_layout.addWidget(widget)
            self.loaded_tasks[task.task_id] = widget

        self.current_index = len(initial_tasks)
        self.load_all_task_dirs()

    # ========== 新增功能 ==========

    @Slot()
    def refresh_tasks(self):
        """手动刷新：重新加载所有任务"""
        logger.info("手动刷新任务...")
        # Update task manager reference first
        self._update_task_manager_for_current_item()
        
        if self.task_manager is None:
            logger.warning("No task manager available for current timeline item")
            self.clear_tasks()
            return

        self._cancel_task_list_workers()
        tm = self.task_manager

        def fetch():
            return tm.load_all_tasks_thread_worker()

        def on_finished(loaded):
            self._tasks_refresh_worker = None
            try:
                tm.tasks.clear()
                for t in loaded:
                    tm.tasks[t.task_id] = t
                self.clear_tasks()
                self.current_index = 0
                self.load_all_task_dirs()
                self.load_more_tasks()
            except Exception as e:
                logger.error(f"刷新任务失败: {e}")
                self.loading = False

        def on_error(msg: str, _exc: Exception):
            self._tasks_refresh_worker = None
            logger.error(f"刷新任务失败: {msg}")
            self.loading = False

        self._tasks_refresh_worker = run_in_background(
            fetch,
            on_finished=on_finished,
            on_error=on_error,
            auto_cleanup=False,
            task_type="task_list_refresh",
        )

    def clear_tasks(self):
        """清空当前任务列表"""
        for widget in self.loaded_tasks.values():
            widget.clicked.disconnect(self.on_task_item_clicked)
            widget.setParent(None)
            widget.deleteLater()
        self.loaded_tasks.clear()
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.takeAt(i).widget().deleteLater()
        
        # Clear the selection
        self.selected_task_widget = None
        # Hide preview panel
        self.hide_preview_panel()

    def on_task_progress_update(self, progress):
        """Handle task progress updates from workspace"""
        try:
            # Extract task info from progress object
            task_progress_obj = progress  # progress is already a TaskProgress instance
            task = task_progress_obj.task
            task_id = task.task_id  # Use the task's actual ID instead of extracting from path
            percent = task_progress_obj.percent
            logs = task_progress_obj.logs

            # Find the corresponding widget and update it
            if task_id in self.loaded_tasks:
                task_widget = self.loaded_tasks[task_id]

                # Update task properties directly
                task.percent = percent
                task.log = logs

                task_widget.update_display(task)
                logger.info(f"Updated task {task_id} progress to {percent}%")
            else:
                # Task might not be loaded yet, refresh the task list if needed
                # For now we just log this case
                logger.debug(f"Progress update for unloaded task {task_id}, skipping update")
        except Exception as e:
            logger.error(f"Error handling task progress update: {e}", exc_info=True)
    
    def on_project_switched(self, project_name):
        """处理项目切换"""
        # Update task manager for the new project's current timeline item
        self._update_task_manager_for_current_item()
        
        # 刷新任务以确保显示新项目中的任务
        self.refresh_tasks()
        
        # Hide the preview panel on project switch
        if hasattr(self, 'preview_panel'):
            self.preview_panel.hide()