"""Character panel for role/actor management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QMessageBox

from app.data.character import Character, CharacterManager
from app.data.workspace import Workspace
from app.ui.panels.actor.actor_edit_dialog import ActorEditDialog
from app.ui.panels.actor.actor_panel_view_model import ActorListModel, ActorPanelViewModel, _ActorRow
from app.ui.panels.base_panel import BasePanel
from utils.i18n_utils import tr
from utils.thread_utils import ThreadSafetyMixin

logger = logging.getLogger(__name__)


class ActorPanel(ThreadSafetyMixin, BasePanel):
    """Panel for role/actor management."""

    character_selected = Signal(str)  # character_name

    def __init__(self, workspace: Workspace, parent=None):
        ThreadSafetyMixin.__init__(self)
        BasePanel.__init__(self, workspace, parent)
        self.character_manager: Optional[CharacterManager] = None

    def setup_ui(self):
        self.set_panel_title(tr("Characters"))

        self.actor_model = ActorListModel(self)
        self.actor_view_model = ActorPanelViewModel(self)
        self.actor_view_model.set_empty_message(tr("暂无角色，点击新建角色创建。"))

        self.actor_quick = QQuickWidget(self)
        self.actor_quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.actor_quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self.actor_quick.setClearColor(Qt.transparent)
        self.actor_quick.rootContext().setContextProperty("actorModel", self.actor_model)
        self.actor_quick.rootContext().setContextProperty("actorPanelViewModel", self.actor_view_model)
        qml_path = Path(__file__).resolve().parent.parent.parent / "qml" / "panels" / "ActorPanel.qml"
        self.actor_quick.setSource(QUrl.fromLocalFile(str(qml_path)))
        if self.actor_quick.status() == QQuickWidget.Error:
            for e in self.actor_quick.errors():
                logger.error("ActorPanel QML error: %s", e.toString())
        self.content_layout.addWidget(self.actor_quick)

        self.actor_view_model.addRequested.connect(self._on_add_character)
        self.actor_view_model.drawRequested.connect(self._on_draw_character)
        self.actor_view_model.extractRequested.connect(self._on_extract_character)
        self.actor_view_model.actorClicked.connect(self._on_character_clicked)
        self.actor_view_model.actorDoubleClicked.connect(self._on_edit_character)
        self.actor_view_model.actorSelectionChanged.connect(self._on_character_selection_changed)

    def _connect_signals(self):
        if self.character_manager:
            try:
                self.character_manager.character_added.disconnect(self._on_character_added)
                self.character_manager.character_updated.disconnect(self._on_character_updated)
                self.character_manager.character_deleted.disconnect(self._on_character_deleted)
            except Exception:
                pass
            self.character_manager.character_added.connect(self._on_character_added)
            self.character_manager.character_updated.connect(self._on_character_updated)
            self.character_manager.character_deleted.connect(self._on_character_deleted)

    def _on_add_character(self):
        if not self.character_manager:
            QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
            return
        dialog = ActorEditDialog(self.character_manager, parent=self)
        dialog.character_saved.connect(self._on_character_saved)
        dialog.exec()

    def _on_draw_character(self):
        QMessageBox.information(self, tr("提示"), tr("抽卡功能开发中..."))

    def _on_extract_character(self):
        QMessageBox.information(self, tr("提示"), tr("提取功能开发中..."))

    def _on_character_clicked(self, character_name: str):
        self.character_selected.emit(character_name)

    def _on_character_selection_changed(self, character_name: str, is_selected: bool):
        self.actor_model.set_selected_by_name(character_name, is_selected)
        if is_selected:
            self.character_selected.emit(character_name)

    def _on_edit_character(self, character_name: str):
        if not self.character_manager:
            QMessageBox.warning(self, tr("错误"), tr("角色管理器未初始化，请检查项目配置"))
            return
        dialog = ActorEditDialog(self.character_manager, character_name, parent=self)
        dialog.character_saved.connect(self._on_character_saved)
        dialog.exec()

    def _character_to_row(self, character: Character) -> _ActorRow:
        image_path = character.get_absolute_resource_path("main_view") or ""
        return _ActorRow(
            name=character.name,
            description=character.description or "",
            image_path=image_path,
            selected=False,
        )

    def _load_characters(self):
        if not self.character_manager:
            return

        self.show_loading(tr("正在加载角色..."))

        try:
            characters = self.character_manager.list_characters()
            self._on_characters_loaded(characters)
        except Exception as e:
            self._on_load_error(str(e), e)

    def _on_characters_loaded(self, characters: List[Character]):
        rows = [self._character_to_row(c) for c in characters]
        self.actor_model.set_rows(rows)
        self.hide_loading()

    def _on_load_error(self, error_msg: str, exception: Exception):
        logger.error(f"❌ Error loading actor manager: {error_msg}")
        logger.error(f"Exception: {exception}", exc_info=True)
        self._data_loaded = True
        self.hide_loading()

    def _on_character_saved(self, character_name: str):
        self._load_characters()

    def _on_character_added(self, character: Character):
        self._load_characters()

    def _on_character_updated(self, character: Character):
        self._load_characters()

    def _on_character_deleted(self, character_name: str):
        self._load_characters()

    def load_data(self):
        def _load_character_manager():
            project = self.workspace.get_project()
            if not project:
                return None
            return project.get_character_manager()

        self.show_loading(tr("正在加载角色管理器..."))
        self.safe_run_in_background(
            _load_character_manager,
            on_finished=self._on_character_manager_loaded,
            on_error=self._on_load_error,
        )

    def _on_character_manager_loaded(self, character_manager):
        if character_manager:
            self.character_manager = character_manager
            self._connect_signals()
            self._data_loaded = True
            self._load_characters()
        else:
            self._data_loaded = True
            self.actor_model.set_rows([])
            self.hide_loading()

    def on_activated(self):
        super().on_activated()
        if self._data_loaded and self.character_manager:
            self._connect_signals()
            self._load_characters()
        logger.info("✅ Character panel activated")

    def on_deactivated(self):
        self.cleanup_workers_on_deactivate()
        super().on_deactivated()
        logger.info("⏸️ Character panel deactivated")

    def on_project_switched(self, project_name: str):
        self._data_loaded = False
        self.character_manager = None
        self.actor_model.set_rows([])
        super().on_project_switched(project_name)
