"""
Main widget for video export functionality
"""
import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices

from app.core.task_manager import TaskManager
from app.ui.base_widget import BaseWidget
from app.workers import TimelineExportWorker
from utils.i18n_utils import tr, translation_manager


class ExportVideoWidget(BaseWidget):
    """
    Main export video widget that provides UI controls for exporting timeline items
    """
    
    def __init__(self, workspace):
        super().__init__(workspace)
        self.setObjectName("ExportVideoWidget")
        
        # Store reference to workspace to access timeline
        self.workspace = workspace
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI for the export video widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Export options
        options_group = QGroupBox(tr("导出选项"))
        options_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 6px;
                margin-top: 1ex;
                padding-top: 8px;
                padding-left: 5px;
                padding-right: 5px;
                padding-bottom: 8px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
        """)
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)
        
        # Quick export buttons
        quick_buttons_layout = QHBoxLayout()
        
        self.export_all_button = QPushButton(tr("导出所有为一个视频"))
        self.export_all_button.setToolTip(tr("将所有时间线项导出为单个视频"))
        self.export_all_button.setStyleSheet("""
            QPushButton {
                background-color: #4e73df;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #2e59d9;
            }
            QPushButton:pressed {
                background-color: #2653d4;
            }
        """)
        
        self.export_grouped_button = QPushButton(tr("分组导出"))
        self.export_grouped_button.setToolTip(tr("将时间线项分N组导出"))
        self.export_grouped_button.setStyleSheet("""
            QPushButton {
                background-color: #4e73df;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #2e59d9;
            }
            QPushButton:pressed {
                background-color: #2653d4;
            }
        """)
        
        self.export_individual_button = QPushButton(tr("逐个导出")) 
        self.export_individual_button.setToolTip(tr("将每个项导出为单独的视频"))
        self.export_individual_button.setStyleSheet("""
            QPushButton {
                background-color: #4e73df;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #2e59d9;
            }
            QPushButton:pressed {
                background-color: #2653d4;
            }
        """)
        
        quick_buttons_layout.addWidget(self.export_all_button)
        quick_buttons_layout.addWidget(self.export_grouped_button) 
        quick_buttons_layout.addWidget(self.export_individual_button)
        quick_buttons_layout.setSpacing(8)
        
        options_layout.addLayout(quick_buttons_layout)
        
        # Advanced options panel (always visible now)
        self.advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_panel)
        self.advanced_panel.setVisible(True)  # Always visible now
        self.advanced_panel.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 4px;
                padding: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # FPS setting
        fps_layout = QHBoxLayout()
        fps_label = QLabel(tr("帧率:"))
        fps_label.setStyleSheet("font-weight: bold; color: #495057; min-width: 130px;")
        fps_layout.addWidget(fps_label)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(30)
        self.fps_spin.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #ced4da;
                border-radius: 3px;
                min-width: 70px;
                background-color: #ffffff;
                selection-background-color: #4e73df;
            }
            QSpinBox:focus {
                border: 1px solid #4e73df;
                outline: none;
            }
        """)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        advanced_layout.addLayout(fps_layout) 
        
        # Items per video (for grouped export)
        items_per_video_layout = QHBoxLayout()
        items_per_video_label = QLabel(tr("每个视频的项数（分组导出）:"))
        items_per_video_label.setStyleSheet("font-weight: bold; color: #495057; min-width: 130px;")
        items_per_video_layout.addWidget(items_per_video_label)
        self.items_per_video_spin = QSpinBox()
        self.items_per_video_spin.setRange(1, 100)
        self.items_per_video_spin.setValue(10)
        self.items_per_video_spin.setStyleSheet("""
            QSpinBox {
                padding: 4px;
                border: 1px solid #ced4da;
                border-radius: 3px;
                min-width: 70px;
                background-color: #ffffff;
                selection-background-color: #4e73df;
            }
            QSpinBox:focus {
                border: 1px solid #4e73df;
                outline: none;
            }
        """)
        items_per_video_layout.addWidget(self.items_per_video_spin)
        items_per_video_layout.addStretch()
        advanced_layout.addLayout(items_per_video_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel(tr("输出目录:"))
        output_label.setStyleSheet("font-weight: bold; color: #495057; min-width: 130px;")
        output_layout.addWidget(output_label)
        self.output_dir_label = QLabel(os.path.expanduser("~"))
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 5px;
                color: #495057;
            }
        """)
        output_layout.addWidget(self.output_dir_label)
        
        # Add both browse and save as buttons
        self.browse_button = QPushButton(tr("浏览..."))
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #1cc88a;
                color: white;
                border: none;
                padding: 6px 8px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #17a279;
            }
            QPushButton:pressed {
                background-color: #148966;
            }
        """)
        output_layout.addWidget(self.browse_button)
        
        self.save_as_button = QPushButton(tr("另存为..."))
        self.save_as_button.setStyleSheet("""
            QPushButton {
                background-color: #36b9cc;
                color: white;
                border: none;
                padding: 6px 8px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #2c97a8;
            }
            QPushButton:pressed {
                background-color: #268490;
            }
        """)
        output_layout.addWidget(self.save_as_button)
        advanced_layout.addLayout(output_layout)
        
        options_layout.addWidget(self.advanced_panel)
        
        layout.addWidget(options_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: #e9ecef;
                text-align: center;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #4e73df;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Export button
        self.export_button = QPushButton(tr("导出"))
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #36b9cc;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2c97a8;
            }
            QPushButton:pressed {
                background-color: #268490;
            }
        """)
        layout.addWidget(self.export_button)
        
        layout.addStretch()  # Add stretch to push everything up
        
        # Connect to language change signal
        translation_manager.language_changed.connect(self.retranslateUi)
        
    def retranslateUi(self):
        """更新所有UI文本当语言变化时"""
        # Update buttons
        self.export_all_button.setText(tr("导出所有为一个视频"))
        self.export_all_button.setToolTip(tr("将所有时间线项导出为单个视频"))
        self.export_grouped_button.setText(tr("分组导出"))
        self.export_grouped_button.setToolTip(tr("将时间线项分N组导出"))
        self.export_individual_button.setText(tr("逐个导出"))
        self.export_individual_button.setToolTip(tr("将每个项导出为单独的视频"))
    def retranslateUi(self):
        """Update all UI text when language changes"""
        # Block signals during update to prevent unwanted events
        widgets_to_block = [
            self.export_all_button,
            self.export_grouped_button,
            self.export_individual_button,
            self.browse_button,
            self.save_as_button,
            self.export_button
        ]
        
        for widget in widgets_to_block:
            widget.blockSignals(True)
        
        # Update buttons
        self.export_all_button.setText(tr("导出所有为一个视频"))
        self.export_all_button.setToolTip(tr("将所有时间线项导出为单个视频"))
        self.export_grouped_button.setText(tr("分组导出"))
        self.export_grouped_button.setToolTip(tr("将时间线项分N组导出"))
        self.export_individual_button.setText(tr("逐个导出"))
        self.export_individual_button.setToolTip(tr("将每个项导出为单独的视频"))
        self.browse_button.setText(tr("浏览..."))
        self.save_as_button.setText(tr("另存为..."))
        self.export_button.setText(tr("导出"))
        
        # Re-enable signals
        for widget in widgets_to_block:
            widget.blockSignals(False)
        
        # Update group box and labels without triggering layout recalculations
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QGroupBox):
                    widget.setTitle(tr("导出选项"))
                    # Update labels inside - but be careful not to trigger resize
                    self._update_labels_recursive(widget)
                    break
    
    def _update_labels_recursive(self, parent):
        """递归更新所有标签 - 仅当文本实际变化时更新"""
        if hasattr(parent, 'layout') and parent.layout():
            layout = parent.layout()
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item:
                    if item.widget():
                        widget = item.widget()
                        if isinstance(widget, QLabel):
                            old_text = widget.text()
                            new_text = None
                            
                            # Determine new text based on current text
                            if "帧率" in old_text or "FPS" in old_text:
                                new_text = tr("帧率:")
                            elif "每个视频" in old_text or "Items per video" in old_text:
                                new_text = tr("每个视频的项数（分组导出）:")
                            elif "输出目录" in old_text or "Output Directory" in old_text:
                                new_text = tr("输出目录:")
                            
                            # Only update if text changed
                            if new_text and old_text != new_text:
                                widget.setText(new_text)
                        elif hasattr(widget, 'layout'):
                            self._update_labels_recursive(widget)
                    elif item.layout():
                        self._update_labels_recursive(item.layout())
    
    def connect_signals(self):
        """Connect UI signals"""
        # Quick export buttons
        self.export_all_button.clicked.connect(self._export_all)
        self.export_grouped_button.clicked.connect(self._export_grouped)
        self.export_individual_button.clicked.connect(self._export_individual)
        
        # Browse button
        self.browse_button.clicked.connect(self._browse_directory)
        
        # Save As button
        self.save_as_button.clicked.connect(self._save_as_directory)
        
        # Main export button - now triggers export directly
        self.export_button.clicked.connect(self._start_export)
        
    
            
    def _browse_directory(self):
        """Open directory browser dialog"""
        project = self.workspace.get_project()
        last_dir = project.config.get('last_export_dir', os.path.expanduser("~"))
        
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("选择导出目录"),
            last_dir
        )
        
        if directory:
            self.output_dir_label.setText(directory)
            # Save the last export directory
            project.update_config('last_export_dir', directory)
    
    def _save_as_directory(self):
        """Open save as dialog to select export directory"""
        project = self.workspace.get_project()
        last_dir = project.config.get('last_export_dir', os.path.expanduser("~"))
        
        # Use getSaveFileName but we'll just use the directory part
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("保存导出视频"),
            os.path.join(last_dir, "exported_video.mp4"),
            tr("视频文件 (*.mp4 *.avi *.mov);;所有文件 (*)")
        )
        
        if file_path:
            # Extract directory from the file path
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            # Save the directory as the export location
            self.output_dir_label.setText(directory)
            # Save the last export directory
            project.update_config('last_export_dir', directory)
            
            # Store the desired filename for use during export
            self.desired_export_filename = os.path.splitext(filename)[0]  # Without extension
    
    def _export_all(self):
        """Prepare to export all items as one video"""
        self._prepare_and_start_export('all_as_one')
    
    def _export_grouped(self):
        """Prepare to export items in groups"""
        self._prepare_and_start_export('grouped')
    
    def _export_individual(self):
        """Prepare to export items individually"""
        self._prepare_and_start_export('individual')
    
    def _start_export(self):
        """Start the export process directly from this widget"""
        # Determine export mode based on which quick button was most recently used
        # For now, we'll use a default mode or add radio buttons to this widget
        # We'll implement the export mode selection more explicitly
        
        # If no advanced panel is shown, default to 'all_as_one'
        if not self.advanced_panel.isVisible():
            export_mode = 'all_as_one'
        else:
            # For floating panel, we'll add radio buttons to maintain flexibility
            # For now, default to all_as_one
            export_mode = 'all_as_one'
        
        self._prepare_and_start_export(export_mode)

    def _prepare_and_start_export(self, export_mode):
        """Prepare export with given mode and start the process"""
        # Validate export directory
        output_dir = self.output_dir_label.text()
        if not os.path.exists(output_dir):
            QMessageBox.warning(self, tr("警告"), tr("导出目录不存在！"))
            return
        
        # Disable UI during export
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Get timeline items
        timeline = self.workspace.get_project().get_timeline()
        timeline_items = timeline.get_items()  # Assuming this returns items in order
        
        if not timeline_items:
            QMessageBox.warning(self, tr("警告"), tr("没有时间线项可导出！"))
            self._set_ui_enabled(True)
            self.progress_bar.setVisible(False)
            return
        
        # Prepare export parameters
        export_params = {
            'timeline_items': timeline_items,
            'export_mode': export_mode,
            'items_per_video': self.items_per_video_spin.value(),
            'output_dir': output_dir,
            'fps': self.fps_spin.value()
        }
        
        # Save the last export directory
        project = self.workspace.get_project()
        project.update_config('last_export_dir', output_dir)
        
        # Store the export directory to use after export finishes
        self.last_export_dir = output_dir
        
        worker = TimelineExportWorker(export_params)
        worker.signals.progress.connect(
            lambda _task_id, percent, _msg: self._update_progress(percent)
        )
        worker.signals.finished.connect(lambda _task_id, _result: self._export_finished())
        worker.signals.error.connect(
            lambda _task_id, msg, _exc: self._export_error(msg)
        )
        self.export_worker = worker
        TaskManager.instance().submit(worker)

    def _update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)

    def _export_finished(self):
        """Handle export completion"""
        # Show success message and open the export directory automatically
        # Open the export directory in the system file explorer
        export_dir = self.last_export_dir
        if os.path.exists(export_dir):
            QDesktopServices.openUrl(f"file://{export_dir}")
        
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)

    def _export_error(self, error_msg):
        """Handle export error"""
        QMessageBox.critical(self, tr("错误"), tr("导出失败: {}").format(error_msg))
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)

    def _set_ui_enabled(self, enabled):
        """Enable/disable UI elements"""
        # Enable/disable all the main controls
        self.export_all_button.setEnabled(enabled)
        self.export_grouped_button.setEnabled(enabled)
        self.export_individual_button.setEnabled(enabled)
        self.fps_spin.setEnabled(enabled)
        self.items_per_video_spin.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        self.save_as_button.setEnabled(enabled)
        self.export_button.setEnabled(enabled)
        
        # Update advanced panel controls
        self.items_per_video_spin.setEnabled(enabled)


class FloatingExportPanel(QFrame):
    """
    A floating panel for video export functionality
    """
    
    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.setObjectName("FloatingExportPanel")
        
        # Set window flags to make it a floating window
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # Set initial size
        self.setFixedWidth(360)
        self.setMinimumHeight(500)
        
        # Create the export widget
        self.export_widget = ExportVideoWidget(workspace)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Top margin for title bar
        layout.setSpacing(10)
        
        # Title bar
        title_bar = self._create_title_bar()
        layout.addWidget(title_bar)
        
        # Add export widget
        layout.addWidget(self.export_widget)
        
        # Add close functionality
        self.export_widget.export_button.clicked.connect(self._on_export_started)
        
        # Styling
        self.setStyleSheet("""
            FloatingExportPanel {
                background-color: #000000;
                border: 1px solid #000000;
                border-radius: 0px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
        """)
        
        # Store title label reference for retranslateUi
        self.title_label = None
        
        # Connect to language change signal
        translation_manager.language_changed.connect(self.retranslateUi)

    def _create_title_bar(self):
        """Create a title bar with minimize and close buttons"""
        title_bar = QWidget()
        title_bar.setFixedHeight(25)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #495057;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        title_layout.setSpacing(0)
        
        # Title label
        title_label = QLabel(tr("导出视频"))
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        title_layout.addWidget(title_label)
        
        # Store reference for retranslateUi
        self.title_label = title_label
        
        title_layout.addStretch()
        
        # Close button
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #e74a3b;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d13a2b;
            }
            QPushButton:pressed {
                background-color: #b92c1f;
            }
        """)
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        
        return title_bar
    
    def retranslateUi(self):
        """更新所有UI文本当语言变化时"""
        if self.title_label:
            self.title_label.setText(tr("导出视频"))

    def _on_export_started(self):
        """Called when export starts - disable panel during export"""
        # The export widget handles its own UI enabling/disabling
        # But we can add any additional logic here if needed
        pass

    def update_position(self, parent_pos, parent_size):
        """Update position relative to parent window"""
        # Position the panel in the top-right corner of the parent
        x = parent_pos.x() + parent_size.width() - self.width() - 20
        y = parent_pos.y() + 40  # Offset from top
        
        self.move(x, y)