"""
Character Edit Dialog

Custom dialog for editing actor information including:
- Basic info (name, description, story)
- Relationships
- Resource files (images for different views)
"""

import os
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QFormLayout, QFrame,
    QMessageBox, QFileDialog, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

from app.ui.dialog.custom_dialog import CustomDialog
from app.ui.media_selector.media_selector import MediaSelector
from app.data.character import Character, CharacterManager
from utils.i18n_utils import tr


class ActorEditDialog(CustomDialog):
    """Dialog for editing actor information"""
    
    character_saved = Signal(str)  # character_name
    
    def __init__(self, character_manager: CharacterManager, character_name: Optional[str] = None, parent=None):
        """Initialize actor edit dialog
        
        Args:
            character_manager: CharacterManager instance
            character_name: Character name if editing existing actor, None for new actor
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.character_manager = character_manager
        self.character_name = character_name
        self.character: Optional[Character] = None
        self.is_new_character = character_name is None
        
        # Resource selectors: resource_type -> MediaSelector
        self.resource_selectors: Dict[str, MediaSelector] = {}
        
        # Form widgets
        self.name_input: Optional[QLineEdit] = None
        self.description_input: Optional[QTextEdit] = None
        self.story_input: Optional[QTextEdit] = None
        
        # Relationships widget (simplified - can be enhanced later)
        self.relationships_input: Optional[QTextEdit] = None
        
        self._init_ui()
        self._load_character()
    
    def _init_ui(self):
        """Initialize the UI"""
        title = tr("新建角色") if self.is_new_character else tr("编辑角色")
        self.set_title(title)
        self.setMinimumSize(800, 700)
        self.setModal(True)
        
        # Create scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Basic information section
        self._create_basic_info_section(content_layout)
        
        # Resources section
        self._create_resources_section(content_layout)
        
        # Relationships section
        self._create_relationships_section(content_layout)
        
        # Add stretch
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        self.setContentWidget(scroll_area)
        
        # Add buttons
        self.add_button(tr("取消"), self.reject, "reject")
        self.add_button(tr("保存"), self._on_save_clicked, "accept")
    
    def _create_basic_info_section(self, parent_layout: QVBoxLayout):
        """Create basic information section"""
        section = self._create_section(tr("基本信息"))
        layout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("输入角色名称"))
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                border: 1px solid #3d3f4e;
                border-radius: 4px;
                padding: 8px;
                color: #e1e1e1;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4080ff;
            }
        """)
        layout.addRow(tr("名称:"), self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(tr("输入角色描述"))
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet("""
            QTextEdit {
                background-color: #1e1f22;
                border: 1px solid #3d3f4e;
                border-radius: 4px;
                padding: 8px;
                color: #e1e1e1;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #4080ff;
            }
        """)
        layout.addRow(tr("描述:"), self.description_input)
        
        # Story
        self.story_input = QTextEdit()
        self.story_input.setPlaceholderText(tr("输入角色故事/背景"))
        self.story_input.setMaximumHeight(150)
        self.story_input.setStyleSheet("""
            QTextEdit {
                background-color: #1e1f22;
                border: 1px solid #3d3f4e;
                border-radius: 4px;
                padding: 8px;
                color: #e1e1e1;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #4080ff;
            }
        """)
        layout.addRow(tr("故事:"), self.story_input)
        
        section.layout().addLayout(layout)
        parent_layout.addWidget(section)
    
    def _create_resources_section(self, parent_layout: QVBoxLayout):
        """Create resources section"""
        section = self._create_section(tr("角色资源"))
        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create resource selectors for each resource type
        row = 0
        col = 0
        max_cols = 3
        
        for resource_type, display_name in Character.RESOURCE_TYPES.items():
            if resource_type == 'other':
                continue  # Skip 'other' for now
            
            # Label
            label = QLabel(display_name + ":")
            label.setStyleSheet("color: #e1e1e1; font-size: 12px;")
            
            # Media selector
            selector = MediaSelector()
            selector.set_supported_types(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'])
            selector.preview_widget.setFixedSize(100, 100)
            selector.placeholder_widget.setFixedSize(100, 100)
            selector.set_placeholder_text(display_name)
            
            self.resource_selectors[resource_type] = selector
            
            # Add to grid
            layout.addWidget(label, row, col * 2)
            layout.addWidget(selector, row, col * 2 + 1)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        section.layout().addLayout(layout)
        parent_layout.addWidget(section)
    
    def _create_relationships_section(self, parent_layout: QVBoxLayout):
        """Create relationships section"""
        section = self._create_section(tr("关系网"))
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Info label
        info_label = QLabel(tr("格式: 角色名称: 关系描述 (每行一个)"))
        info_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Relationships input
        self.relationships_input = QTextEdit()
        self.relationships_input.setPlaceholderText(tr("例如:\n角色A: 好友\n角色B: 敌人"))
        self.relationships_input.setMaximumHeight(120)
        self.relationships_input.setStyleSheet("""
            QTextEdit {
                background-color: #1e1f22;
                border: 1px solid #3d3f4e;
                border-radius: 4px;
                padding: 8px;
                color: #e1e1e1;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #4080ff;
            }
        """)
        layout.addWidget(self.relationships_input)
        
        section.layout().addLayout(layout)
        parent_layout.addWidget(section)
    
    def _create_section(self, title: str) -> QFrame:
        """Create a section frame with title"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #1e1f22;
                border: 1px solid #3d3f4e;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                background-color: #2b2d30;
                color: #e1e1e1;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 15px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        layout.addWidget(title_label)
        
        # Content container
        content_layout = QVBoxLayout()
        layout.addLayout(content_layout)
        
        # Store content layout reference
        section.content_layout = content_layout
        
        return section
    
    def _load_character(self):
        """Load actor data into the form"""
        if self.is_new_character:
            return
        
        self.character = self.character_manager.get_character(self.character_name)
        if not self.character:
            QMessageBox.warning(self, tr("错误"), tr("角色不存在"))
            self.reject()
            return
        
        # Load basic info
        if self.name_input:
            self.name_input.setText(self.character.name)
            self.name_input.setEnabled(False)  # Disable name editing for existing characters
        
        if self.description_input:
            self.description_input.setPlainText(self.character.description)
        
        if self.story_input:
            self.story_input.setPlainText(self.character.story)
        
        # Load resources
        for resource_type, selector in self.resource_selectors.items():
            resource_path = self.character.get_resource_path(resource_type)
            if resource_path:
                abs_path = self.character.get_absolute_resource_path(resource_type)
                if abs_path and os.path.exists(abs_path):
                    selector.set_value(abs_path)
        
        # Load relationships
        if self.relationships_input:
            relationships_text = []
            for char_name, relation_desc in self.character.relationships.items():
                relationships_text.append(f"{char_name}: {relation_desc}")
            self.relationships_input.setPlainText("\n".join(relationships_text))
    
    def _parse_relationships(self) -> Dict[str, str]:
        """Parse relationships from text input
        
        Returns:
            Dictionary mapping actor name to relationship description
        """
        if not self.relationships_input:
            return {}
        
        text = self.relationships_input.toPlainText().strip()
        if not text:
            return {}
        
        relationships = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if ':' in line:
                parts = line.split(':', 1)
                char_name = parts[0].strip()
                relation_desc = parts[1].strip() if len(parts) > 1 else ''
                if char_name:
                    relationships[char_name] = relation_desc
        
        return relationships
    
    def _on_save_clicked(self):
        """Handle save button click"""
        # Validate name
        if not self.name_input:
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, tr("错误"), tr("角色名称不能为空"))
            return
        
        # Get form values
        description = self.description_input.toPlainText().strip() if self.description_input else ''
        story = self.story_input.toPlainText().strip() if self.story_input else ''
        relationships = self._parse_relationships()
        
        try:
            if self.is_new_character:
                # Create new actor
                character = self.character_manager.create_character(name, description, story)
                if not character:
                    QMessageBox.warning(self, tr("错误"), tr("创建角色失败"))
                    return
                
                # Update relationships
                if relationships:
                    self.character_manager.update_character(name, relationships=relationships)
                
                # Add resources
                for resource_type, selector in self.resource_selectors.items():
                    file_path = selector.get_value()
                    if file_path and os.path.exists(file_path):
                        self.character_manager.add_resource(name, resource_type, file_path)
                
                self.character_saved.emit(name)
                self.accept()
            else:
                # Update existing actor
                if name != self.character_name:
                    # Rename actor
                    if not self.character_manager.rename_character(self.character_name, name):
                        QMessageBox.warning(self, tr("错误"), tr("重命名角色失败"))
                        return
                    self.character_name = name
                
                # Update actor properties
                self.character_manager.update_character(
                    name,
                    description=description,
                    story=story,
                    relationships=relationships
                )
                
                # Update resources
                character = self.character_manager.get_character(name)
                if character:
                    # Remove resources that are no longer set
                    for resource_type in Character.RESOURCE_TYPES.keys():
                        if resource_type in self.resource_selectors:
                            selector = self.resource_selectors[resource_type]
                            file_path = selector.get_value()
                            
                            if file_path and os.path.exists(file_path):
                                # Add or update resource
                                self.character_manager.add_resource(name, resource_type, file_path)
                            elif character.resource_exists(resource_type):
                                # Remove resource if it was previously set but now cleared
                                self.character_manager.remove_resource(name, resource_type, remove_file=True)
                
                self.character_saved.emit(name)
                self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, tr("错误"), tr(f"保存角色失败: {str(e)}"))
            logger.error(f"Failed to save character: {e}", exc_info=True)

