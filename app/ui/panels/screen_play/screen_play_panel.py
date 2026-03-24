"""Screen Play panel implemented with QML content."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl, Qt
from PySide6.QtQuickWidgets import QQuickWidget

from app.data.screen_play import ScreenPlayManager, ScreenPlayScene
from app.ui.panels.base_panel import BasePanel
from app.ui.panels.screen_play.screen_play_view_model import _SceneRow, ScreenPlayListModel, ScreenPlayViewModel

logger = logging.getLogger(__name__)


class ScreenPlayPanel(BasePanel):
    """Panel for managing screenplay scenes."""

    def __init__(self, workspace, parent=None):
        self.screenplay_manager = None
        self.current_project = None
        self.current_scene_id = None

        super().__init__(workspace, parent)
        self.set_panel_title("Screen Play")

    def setup_ui(self):
        self.screen_play_model = ScreenPlayListModel(self)
        self.screen_play_view_model = ScreenPlayViewModel(self)

        self.screen_play_quick = QQuickWidget(self)
        self.screen_play_quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.screen_play_quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self.screen_play_quick.setClearColor(Qt.transparent)
        self.screen_play_quick.rootContext().setContextProperty("screenPlayModel", self.screen_play_model)
        self.screen_play_quick.rootContext().setContextProperty("screenPlayViewModel", self.screen_play_view_model)

        qml_path = Path(__file__).resolve().parent.parent.parent / "qml" / "panels" / "ScreenPlayPanel.qml"
        self.screen_play_quick.setSource(QUrl.fromLocalFile(str(qml_path)))
        if self.screen_play_quick.status() == QQuickWidget.Error:
            for e in self.screen_play_quick.errors():
                logger.error("ScreenPlayPanel QML error: %s", e.toString())

        self.content_layout.addWidget(self.screen_play_quick)

        vm = self.screen_play_view_model
        vm.addSceneRequested.connect(self._add_scene)
        vm.refreshRequested.connect(self._refresh_scenes)
        vm.openSceneRequested.connect(self._show_scene_editor)
        vm.returnRequested.connect(self._return_to_list)
        vm.saveRequested.connect(self._save_scene)

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

    def _add_scene(self):
        """Add a new scene to the screenplay."""
        if not self.screenplay_manager:
            return

        scene_index = len(self.screenplay_manager.list_scenes()) + 1
        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        new_scene = ScreenPlayScene(
            scene_id=scene_id,
            title=f"Scene {scene_index}",
            content="# INT. LOCATION - DAY\n\nACTION DESCRIPTION HERE.\n\nCHARACTER NAME\nWhat the character says here.\n\n_CUT TO:_",
            scene_number=str(scene_index),
        )
        success = self.screenplay_manager.create_scene(
            scene_id=new_scene.scene_id,
            title=new_scene.title,
            content=new_scene.content,
            metadata=new_scene.to_dict(),
        )
        if success:
            self._refresh_scenes()

    def _refresh_scenes(self):
        """Refresh the scene list model."""
        model = self.screen_play_model
        vm = self.screen_play_view_model

        if not self.screenplay_manager:
            model.set_rows([])
            vm.set_empty_message("No scenes found. Click 'Add Scene' to create one.")
            vm.set_mode("list")
            return

        scenes = self.screenplay_manager.list_scenes()
        logger.info("Loading %s scenes from screenplay manager", len(scenes))

        def get_scene_sort_key(scene):
            try:
                return (True, int(scene.scene_number), str(scene.scene_number))
            except (ValueError, TypeError):
                return (False, 0, str(scene.scene_number))

        scenes.sort(key=get_scene_sort_key)

        rows = []
        for scene in scenes:
            scene_num = scene.scene_number
            try:
                scene_num = str(int(scene_num))
            except (ValueError, TypeError):
                scene_num = str(scene_num or "")
            rows.append(
                _SceneRow(
                    scene_id=scene.scene_id,
                    title=f"Scene {scene_num}",
                    overview=self._get_scene_overview(scene, scene_num),
                    scene_number=scene_num,
                )
            )
        model.set_rows(rows)
        vm.set_empty_message("No scenes found. Click 'Add Scene' to create one.")

    def _show_scene_editor(self, scene_id: str):
        """Show the scene editor for the selected scene."""
        if not self.screenplay_manager:
            return

        scene = self.screenplay_manager.get_scene(scene_id)
        if not scene:
            return

        self.current_scene_id = scene_id
        vm = self.screen_play_view_model
        vm.set_editing_scene_id(scene_id)
        vm.set_editor_text(scene.content or "")
        vm.set_mode("editor")

    def _return_to_list(self):
        """Return to the list view."""
        vm = self.screen_play_view_model
        vm.set_mode("list")
        vm.set_editing_scene_id("")
        self.current_scene_id = None

    def _save_scene(self, scene_id: str, updated_content: str):
        """Save the current scene."""
        if not self.screenplay_manager or not scene_id:
            return

        success = self.screenplay_manager.update_scene(
            scene_id=scene_id,
            content=updated_content,
        )

        if success:
            self._refresh_scenes()

    def load_data(self):
        """Load screenplay data for the current project."""
        project = self.workspace.get_project()
        if not project:
            self.screen_play_model.set_rows([])
            self.screen_play_view_model.set_mode("list")
            self.screen_play_view_model.set_empty_message("No active project.")
            return

        try:
            self.screenplay_manager = project.get_screenplay_manager()
            self.current_project = project
            self._refresh_scenes()
        except AttributeError:
            self.screenplay_manager = ScreenPlayManager(project.project_path)
            self.current_project = project
            self._refresh_scenes()
        except Exception as e:
            logger.error(f"Error loading screenplay data: {e}", exc_info=True)

    def on_project_switched(self, project_name: str):
        """Called when the project is switched."""
        super().on_project_switched(project_name)
        self.load_data()

    def on_activated(self):
        """Called when the panel becomes visible."""
        super().on_activated()
        self.adjustSize()
        if self.parent():
            self.parent().adjustSize()

        logger.info("ScreenPlayPanel activated, screenplay_manager=%s", self.screenplay_manager is not None)
        if self.screenplay_manager:
            self._refresh_scenes()