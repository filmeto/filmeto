"""QML-backed actor edit dialog."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Property, QUrl, Signal, Slot, QObject, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.data.character import Character, CharacterManager
from app.ui.dialog.custom_dialog import CustomDialog
from app.ui.qml.shared_qml_engine import shared_qml_engine
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ActorEditViewModel(QObject):
    nameChanged = Signal()
    nameEditableChanged = Signal()
    descriptionChanged = Signal()
    storyChanged = Signal()
    relationshipsTextChanged = Signal()
    resourceItemsChanged = Signal()
    saveRequested = Signal()

    def __init__(self, parent_dialog, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._parent_dialog = parent_dialog
        self._name = ""
        self._name_editable = True
        self._description = ""
        self._story = ""
        self._relationships_text = ""
        self._resource_items = []

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        return self._name

    @Property(bool, notify=nameEditableChanged)
    def nameEditable(self) -> bool:
        return self._name_editable

    @Property(str, notify=descriptionChanged)
    def description(self) -> str:
        return self._description

    @Property(str, notify=storyChanged)
    def story(self) -> str:
        return self._story

    @Property(str, notify=relationshipsTextChanged)
    def relationshipsText(self) -> str:
        return self._relationships_text

    @Property("QVariantList", notify=resourceItemsChanged)
    def resourceItems(self):
        return self._resource_items

    def set_name(self, value: str):
        if self._name != value:
            self._name = value
            self.nameChanged.emit()

    def set_name_editable(self, value: bool):
        if self._name_editable != value:
            self._name_editable = value
            self.nameEditableChanged.emit()

    def set_description(self, value: str):
        if self._description != value:
            self._description = value
            self.descriptionChanged.emit()

    def set_story(self, value: str):
        if self._story != value:
            self._story = value
            self.storyChanged.emit()

    def set_relationships_text(self, value: str):
        if self._relationships_text != value:
            self._relationships_text = value
            self.relationshipsTextChanged.emit()

    def set_resource_items(self, items):
        self._resource_items = items
        self.resourceItemsChanged.emit()

    @Slot(str)
    def on_name_changed(self, value: str):
        self.set_name(value or "")

    @Slot(str)
    def on_description_changed(self, value: str):
        self.set_description(value or "")

    @Slot(str)
    def on_story_changed(self, value: str):
        self.set_story(value or "")

    @Slot(str)
    def on_relationships_changed(self, value: str):
        self.set_relationships_text(value or "")

    @Slot(str)
    def pick_resource(self, resource_type: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self._parent_dialog,
            tr("选择资源文件"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
        )
        if not file_path:
            return
        items = list(self._resource_items)
        for item in items:
            if item["key"] == resource_type:
                item["path"] = file_path
                break
        self.set_resource_items(items)

    @Slot(str)
    def clear_resource(self, resource_type: str):
        items = list(self._resource_items)
        for item in items:
            if item["key"] == resource_type:
                item["path"] = ""
                break
        self.set_resource_items(items)


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

        self._view_model = ActorEditViewModel(self, self)

        self._init_ui()
        self._load_character()

    def _init_ui(self):
        title = tr("新建角色") if self.is_new_character else tr("编辑角色")
        self.set_title(title)
        self.setMinimumSize(800, 700)
        self.setModal(True)

        quick = QQuickWidget(shared_qml_engine(), self)
        quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        quick.setAttribute(Qt.WA_TranslucentBackground, True)
        quick.setClearColor(Qt.transparent)
        quick.rootContext().setContextProperty("actorEditViewModel", self._view_model)
        qml_path = Path(__file__).resolve().parent.parent.parent / "qml" / "dialog" / "ActorEditDialog.qml"
        quick.setSource(QUrl.fromLocalFile(str(qml_path)))
        if quick.status() == QQuickWidget.Error:
            for e in quick.errors():
                logger.error("ActorEditDialog QML error: %s", e.toString())
        self.setContentWidget(quick)

        self.add_button(tr("取消"), self.reject, "reject")
        self.add_button(tr("保存"), self._on_save_clicked, "accept")

    def _build_resource_items(self) -> list[dict]:
        items = []
        for resource_type, display_name in Character.RESOURCE_TYPES.items():
            if resource_type == "other":
                continue
            items.append({"key": resource_type, "label": display_name, "path": ""})
        return items

    def _load_character(self):
        self._view_model.set_resource_items(self._build_resource_items())

        if self.is_new_character:
            return

        self.character = self.character_manager.get_character(self.character_name)
        if not self.character:
            QMessageBox.warning(self, tr("错误"), tr("角色不存在"))
            self.reject()
            return

        self._view_model.set_name(self.character.name)
        self._view_model.set_name_editable(False)
        self._view_model.set_description(self.character.description or "")
        self._view_model.set_story(self.character.story or "")

        relationships_text = []
        for char_name, relation_desc in self.character.relationships.items():
            relationships_text.append(f"{char_name}: {relation_desc}")
        self._view_model.set_relationships_text("\n".join(relationships_text))

        items = self._build_resource_items()
        for item in items:
            abs_path = self.character.get_absolute_resource_path(item["key"])
            if abs_path and os.path.exists(abs_path):
                item["path"] = abs_path
        self._view_model.set_resource_items(items)

    def _parse_relationships(self) -> Dict[str, str]:
        text = (self._view_model.relationshipsText or "").strip()
        if not text:
            return {}

        relationships = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if ":" in line:
                parts = line.split(":", 1)
                char_name = parts[0].strip()
                relation_desc = parts[1].strip() if len(parts) > 1 else ""
                if char_name:
                    relationships[char_name] = relation_desc

        return relationships

    def _on_save_clicked(self):
        name = (self._view_model.name or "").strip()
        if not name:
            QMessageBox.warning(self, tr("错误"), tr("角色名称不能为空"))
            return

        description = (self._view_model.description or "").strip()
        story = (self._view_model.story or "").strip()
        relationships = self._parse_relationships()

        try:
            if self.is_new_character:
                character = self.character_manager.create_character(name, description, story)
                if not character:
                    QMessageBox.warning(self, tr("错误"), tr("创建角色失败"))
                    return

                if relationships:
                    self.character_manager.update_character(name, relationships=relationships)

                for item in self._view_model.resourceItems:
                    file_path = item.get("path", "")
                    if file_path and os.path.exists(file_path):
                        self.character_manager.add_resource(name, item["key"], file_path)

                self.character_saved.emit(name)
                self.accept()
            else:
                if name != self.character_name:
                    if not self.character_manager.rename_character(self.character_name, name):
                        QMessageBox.warning(self, tr("错误"), tr("重命名角色失败"))
                        return
                    self.character_name = name

                self.character_manager.update_character(
                    name,
                    description=description,
                    story=story,
                    relationships=relationships,
                )

                character = self.character_manager.get_character(name)
                if character:
                    for resource_type in Character.RESOURCE_TYPES.keys():
                        if resource_type == "other":
                            continue
                        row = next((x for x in self._view_model.resourceItems if x["key"] == resource_type), None)
                        file_path = row.get("path", "") if row else ""
                        if file_path and os.path.exists(file_path):
                            self.character_manager.add_resource(name, resource_type, file_path)
                        elif character.resource_exists(resource_type):
                            self.character_manager.remove_resource(name, resource_type, remove_file=True)

                self.character_saved.emit(name)
                self.accept()

        except Exception as e:
            QMessageBox.critical(self, tr("错误"), tr(f"保存角色失败: {str(e)}"))
            logger.error(f"Failed to save character: {e}", exc_info=True)
