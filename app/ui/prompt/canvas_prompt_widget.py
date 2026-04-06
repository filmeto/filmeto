from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QEvent, Slot, QRect, QPoint
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, 
                               QPushButton, QLabel, QListWidget, QDialog, 
                               QFileDialog, QLineEdit, QMessageBox, QScrollArea,
                               QFrame, QSizePolicy)
from PySide6.QtGui import QCursor, QTextCursor, QKeyEvent

from app.ui.base_widget import BaseWidget, BaseTaskWidget
from app.ui.editor.editor_tool_strip import EditorToolStripWidget
from app.ui.prompt.template_item_widget import TemplateItemWidget
from app.data.workspace import Workspace, PromptTemplate, PromptManager
from utils.i18n_utils import tr, translation_manager


class CanvasPromptWidget(BaseTaskWidget):
    """
    Reusable prompt input component with template management
    """
    
    # Signals
    prompt_submitted = Signal(str)  # Emitted when send button clicked
    prompt_changed = Signal(str)    # Emitted when text changes
    
    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)
        
        self.prompt_manager: PromptManager = workspace.get_prompt_manager()
        
        # State variables
        self._has_focus = False
        self._mouse_over = False
        self._current_text = ""
        self._selected_template = None
        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(300)  # 300ms debounce
        self._in_input_mode = False  # Track if user is actually inputting text
        self._editor_tool_strip: Optional[EditorToolStripWidget] = None

        self._setup_ui()
        self._connect_signals()
        self._apply_initial_style()
        self._update_ui_text()
        
        # Set size policy to expand and fill parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect to language change signal (use lambda to handle optional parameter)
        translation_manager.language_changed.connect(lambda lang: self._update_ui_text())
    
    def _setup_ui(self):
        """Left: narrow category bar. Right work area: top tools, text, bottom config + send."""
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.left_toolbar = QFrame()
        self.left_toolbar.setObjectName("prompt_left_toolbar")
        self.left_toolbar.setFixedWidth(56)
        self.left_toolbar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._left_toolbar_layout = QVBoxLayout(self.left_toolbar)
        self._left_toolbar_layout.setContentsMargins(4, 6, 4, 6)
        self._left_toolbar_layout.setSpacing(0)
        self.left_toolbar.hide()

        self.body = QFrame()
        self.body.setObjectName("prompt_right_panel")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.top_toolbar = QWidget()
        self.top_toolbar.setObjectName("prompt_top_toolbar")
        self.top_toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_toolbar_layout = QHBoxLayout(self.top_toolbar)
        self.top_toolbar_layout.setContentsMargins(8, 6, 8, 4)
        self.top_toolbar_layout.setSpacing(8)

        self.tool_strip_holder = QWidget()
        self.tool_strip_holder.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._tool_strip_holder_layout = QHBoxLayout(self.tool_strip_holder)
        self._tool_strip_holder_layout.setContentsMargins(0, 0, 0, 0)
        self._tool_strip_holder_layout.setSpacing(0)
        self.top_toolbar_layout.addWidget(self.tool_strip_holder, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.top_toolbar_layout.addStretch(1)

        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("prompt_text_edit")
        self.text_edit.setPlaceholderText(tr("Enter your prompt here..."))
        self.text_edit.setMinimumWidth(200)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.installEventFilter(self)

        self.bottom_toolbar = QWidget()
        self.bottom_toolbar.setObjectName("prompt_bottom_toolbar")
        self.bottom_toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        bottom_layout = QHBoxLayout(self.bottom_toolbar)
        bottom_layout.setContentsMargins(8, 4, 8, 6)
        bottom_layout.setSpacing(8)

        self.config_panel_holder = QWidget()
        self.config_panel_holder.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._config_panel_holder_layout = QHBoxLayout(self.config_panel_holder)
        self._config_panel_holder_layout.setContentsMargins(0, 0, 0, 0)
        self._config_panel_holder_layout.setSpacing(0)
        bottom_layout.addWidget(self.config_panel_holder, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.send_button = QPushButton("\ue83e")
        self.send_button.setObjectName("prompt_send_button")
        self.send_button.setFixedSize(44, 44)
        self.send_button.setToolTip(tr("Submit prompt"))
        self.send_button.setCursor(QCursor(Qt.PointingHandCursor))

        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.send_button, 0, Qt.AlignRight | Qt.AlignVCenter)

        body_layout.addWidget(self.top_toolbar, 0)
        body_layout.addWidget(self.text_edit, 0)
        body_layout.addWidget(self.bottom_toolbar, 0)
        self.top_toolbar.hide()

        root.addWidget(self.left_toolbar, 0)
        root.addWidget(self.body, 1)
        self.setLayout(root)
    
    def _connect_signals(self):
        """Connect signals and slots"""
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.send_button.clicked.connect(self._on_send_clicked)

    def _apply_initial_style(self):
        """Apply initial styling"""
        self.setObjectName("CanvasPromptWidget")
        self.setStyleSheet(
            "QWidget#CanvasPromptWidget { background-color: transparent; }"
        )

        self.body.setStyleSheet("""
            QFrame#prompt_right_panel {
                background-color: #2b2d30;
                border: 1px solid #505254;
                border-radius: 8px;
            }
        """)

        self.top_toolbar.setStyleSheet("""
            QWidget#prompt_top_toolbar {
                background-color: #2b2d30;
                border: none;
            }
        """)
        self.bottom_toolbar.setStyleSheet("""
            QWidget#prompt_bottom_toolbar {
                background-color: #2b2d30;
                border: none;
            }
        """)

        self.left_toolbar.setStyleSheet("""
            QFrame#prompt_left_toolbar {
                background-color: transparent;
                border: none;
            }
        """)

        self.text_edit.setStyleSheet("""
            QTextEdit#prompt_text_edit {
                background-color: #2b2d30;
                border: none;
                border-radius: 0px;
                padding: 6px 10px;
                margin: 0px;
                color: #E1E1E1;
                font-size: 14px;
                selection-background-color: #4080ff;
            }
        """)

        self.send_button.setStyleSheet("""
            QPushButton#prompt_send_button {
                font-family: iconfont;
                background-color: #3d3f4e;
                border: none;
                border-radius: 22px;
                color: #E1E1E1;
                font-size: 16px;
            }
            QPushButton#prompt_send_button:hover {
                background-color: #4080ff;
            }
            QPushButton#prompt_send_button:pressed {
                background-color: #3060cc;
            }
        """)
        self._sync_prompt_text_height()

    def _sync_prompt_text_height(self) -> None:
        """One visible line: fixed height from font + vertical padding (scroll for more lines)."""
        vpad = 8 if self._has_focus else 6
        fm = self.text_edit.fontMetrics()
        h = max(26, fm.lineSpacing() + 2 * vpad + 4)
        self.text_edit.setFixedHeight(h)

    
    def eventFilter(self, obj, event):
        """Filter events for text edit widget"""
        if obj == self.text_edit:
            if event.type() == QEvent.FocusIn:
                self._on_input_focus_in()
            elif event.type() == QEvent.FocusOut:
                self._on_input_focus_out()
            elif event.type() == QEvent.Enter:
                self._on_mouse_enter()
            elif event.type() == QEvent.Leave:
                self._on_mouse_leave()
            elif event.type() == QEvent.KeyPress:
                return self._handle_key_press(event)
        
        return super().eventFilter(obj, event)
    
    def _on_input_focus_in(self):
        """Handle input field focus in"""
        self._has_focus = True
        self._update_text_edit_style()
    
    def _on_input_focus_out(self):
        """Handle input field focus out"""
        self._has_focus = False
        self._update_text_edit_style()
    
    def _on_mouse_enter(self):
        """Handle mouse enter event"""
        self._mouse_over = True
    
    def _on_mouse_leave(self):
        """Handle mouse leave event"""
        self._mouse_over = False
    
    def _update_text_edit_style(self):
        """Update text edit style based on focus state only"""
        pad = "8px 10px" if self._has_focus else "6px 10px"
        self.text_edit.setStyleSheet(f"""
            QTextEdit#prompt_text_edit {{
                background-color: #2b2d30;
                border: none;
                border-radius: 0px;
                padding: {pad};
                margin: 0px;
                color: #E1E1E1;
                font-size: 14px;
                selection-background-color: #4080ff;
            }}
        """)
        self._sync_prompt_text_height()
    
    def _on_text_changed(self):
        """Handle text change event"""
        text = self.text_edit.toPlainText()
        self._current_text = text
        
        # Track if user is actually inputting text
        if text.strip() and not self._in_input_mode:
            self._in_input_mode = True
        elif not text.strip() and self._in_input_mode:
            self._in_input_mode = False
        
        # Emit signal
        self.prompt_changed.emit(text)
        
        # Trigger template filtering with debounce
        self._filter_timer.start()
    
    def _on_send_clicked(self):
        """Handle send button click"""
        text = self._current_text.strip()
        
        if not text:
            QMessageBox.warning(self, tr("Empty Input"), tr("Please enter a prompt"))
            return
        
        # Emit signal
        self.prompt_submitted.emit(text)
    
    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events"""
        # Enter key submits (without Ctrl)
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() == Qt.ControlModifier:
                # Ctrl+Enter inserts line break (default behavior)
                return False
            else:
                # Enter submits
                self._on_send_clicked()
                return True

        # Escape closes dropdown
        elif event.key() == Qt.Key_Escape:
            if hasattr(self, 'template_dropdown_container') and self.template_dropdown_container.isVisible():
                self.template_dropdown_container.hide()
                return True

        return False
    
    # Public API
    
    def set_placeholder(self, text: str):
        """Set input field placeholder text"""
        self.text_edit.setPlaceholderText(text)
    
    def get_prompt_text(self) -> str:
        """Retrieve current prompt text"""
        return self._current_text
    
    def clear_prompt(self):
        """Clear input field content"""
        self.text_edit.clear()
        self._current_text = ""

        # Hide template dropdown container if it exists
        if hasattr(self, 'template_dropdown_container'):
            self.template_dropdown_container.hide()

        self._in_input_mode = False  # Reset input mode when clearing

        # Hide token badge if it exists
        if hasattr(self, 'token_badge'):
            self.token_badge.hide()  # Hide token badge
    
    def on_timeline_switch(self, item):
        """Load and display the prompt content from the timeline item"""
        from app.data.timeline import TimelineItem
        if isinstance(item, TimelineItem):
            # Get the current tool name if available - this method can be overridden
            # by parent widgets to provide the selected tool
            tool_name = self.get_current_tool_name()
            
            if tool_name:
                # Load tool-specific prompt
                prompt_content = item.get_prompt(tool_name)
            else:
                # Fallback to general prompt
                prompt_content = item.get_prompt()
                
            if prompt_content is not None:
                self.text_edit.setPlainText(str(prompt_content))
            else:
                # If no prompt in timeline item, clear the input
                self.text_edit.clear()
            self._in_input_mode = False  # Reset input mode when switching timeline
    
    def get_current_tool_name(self) -> str:
        """
        Get the currently selected tool name.
        This method can be overridden by parent widgets to provide the actual selected tool.
        Default implementation returns None.
        """
        return None
    
    def on_project_switched(self, project_name):
        """处理项目切换"""
        # 重新初始化提示管理器
        self.prompt_manager = self.workspace.get_prompt_manager()

        # 清除当前内容
        self.clear_prompt()

        # 隐藏模板下拉框
        if hasattr(self, 'template_dropdown_container'):
            self.template_dropdown_container.hide()
        self._in_input_mode = False  # Reset input mode when switching projects
    
    def set_editor_tool_strip(self, strip: Optional[EditorToolStripWidget]):
        """Place category toggles in the left bar; tool icon stack in the top row of the work area."""
        if not hasattr(self, "_tool_strip_holder_layout") or not hasattr(self, "_left_toolbar_layout"):
            return

        if self._editor_tool_strip and self._editor_tool_strip is not strip:
            old = self._editor_tool_strip
            if old.category_bar:
                old.category_bar.setParent(old)
            if old.tools_stack:
                old.tools_stack.setParent(old)
            old.show()

        while self._left_toolbar_layout.count():
            self._left_toolbar_layout.takeAt(0)

        while self._tool_strip_holder_layout.count():
            item = self._tool_strip_holder_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        self._editor_tool_strip = strip

        if strip and strip.category_bar and strip.tools_stack:
            strip.category_bar.setParent(self.left_toolbar)
            self._left_toolbar_layout.addWidget(
                strip.category_bar, 0, Qt.AlignHCenter | Qt.AlignTop
            )
            self._left_toolbar_layout.addStretch(1)

            strip.tools_stack.setParent(self.tool_strip_holder)
            self._tool_strip_holder_layout.addWidget(strip.tools_stack, 0, Qt.AlignLeft | Qt.AlignVCenter)

            strip.hide()
            self.left_toolbar.show()
            self.top_toolbar.show()
        else:
            self.left_toolbar.hide()
            self.top_toolbar.hide()

    def set_config_panel_widget(self, widget):
        """Place reference image / tool-specific media controls in the bottom toolbar (left of send)."""
        if not hasattr(self, "_config_panel_holder_layout"):
            return

        while self._config_panel_holder_layout.count():
            item = self._config_panel_holder_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if widget:
            widget.setMaximumHeight(120)
            self._config_panel_holder_layout.addWidget(widget, 0, Qt.AlignLeft | Qt.AlignVCenter)
    
    @Slot()
    def _update_ui_text(self):
        """Update all translatable UI text"""
        # Update placeholder
        current_placeholder = self.text_edit.placeholderText()
        new_placeholder = tr("Enter your prompt here...")
        if current_placeholder != new_placeholder:
            self.text_edit.setPlaceholderText(new_placeholder)
        
        # Update tooltip
        current_tooltip = self.send_button.toolTip()
        new_tooltip = tr("Submit prompt")
        if current_tooltip != new_tooltip:
            self.send_button.setToolTip(new_tooltip)