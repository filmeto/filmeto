# -*- coding: utf-8 -*-
"""QML-based startup window."""

import json
import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout

from app.data.workspace import Workspace

logger = logging.getLogger(__name__)
STARTUP_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "StartupWindowRoot.qml"


class _StartupWindowBridge(QObject):
    projectsChanged = Signal()
    selectedProjectChanged = Signal()
    titleChanged = Signal()
    requestEditProject = Signal(str)
    requestCreateProject = Signal(str)
    requestRefreshProjects = Signal()
    requestCloseWindow = Signal()
    requestOpenSettings = Signal()
    requestOpenServerDialog = Signal()
    projectMetaChanged = Signal()
    activePanelChanged = Signal()
    activePanelTitleChanged = Signal()
    memberItemsChanged = Signal()
    screenplayItemsChanged = Signal()
    screenplaySummaryChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects = []
        self._selected_project = ""
        self._title = "Filmeto"
        self._active_panel = "members"
        self._member_items = []
        self._screenplay_items = []
        self._screenplay_summary = ""
        self._timeline_count = "0"
        self._task_count = "0"
        self._budget_text = "$0.00 / $0.00"
        self._story = ""

    @Property("QVariantList", notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property(str, notify=selectedProjectChanged)
    def selectedProject(self):
        return self._selected_project

    @Property(str, notify=titleChanged)
    def title(self):
        return self._title

    @Property(str, notify=activePanelChanged)
    def activePanel(self):
        return self._active_panel

    @Property(str, notify=activePanelTitleChanged)
    def activePanelTitle(self):
        mapping = {
            "members": "Members",
            "screenplay": "Screen Play",
            "plan": "Plan",
        }
        return mapping.get(self._active_panel, "Panel")

    @Property("QVariantList", notify=memberItemsChanged)
    def memberItems(self):
        return self._member_items

    @Property("QVariantList", notify=screenplayItemsChanged)
    def screenplayItems(self):
        return self._screenplay_items

    @Property(str, notify=screenplaySummaryChanged)
    def screenplaySummary(self):
        return self._screenplay_summary

    @Property(str, notify=projectMetaChanged)
    def timelineCount(self):
        return self._timeline_count

    @Property(str, notify=projectMetaChanged)
    def taskCount(self):
        return self._task_count

    @Property(str, notify=projectMetaChanged)
    def budgetText(self):
        return self._budget_text

    @Property(str, notify=projectMetaChanged)
    def storyDescription(self):
        return self._story

    def set_projects(self, projects):
        self._projects = projects
        self.projectsChanged.emit()

    def set_selected_project(self, project_name: str):
        project_name = project_name or ""
        if self._selected_project != project_name:
            self._selected_project = project_name
            self.selectedProjectChanged.emit()

    def set_project_meta(self, *, timeline_count: str, task_count: str, budget_text: str, story: str):
        changed = False
        if self._timeline_count != timeline_count:
            self._timeline_count = timeline_count
            changed = True
        if self._task_count != task_count:
            self._task_count = task_count
            changed = True
        if self._budget_text != budget_text:
            self._budget_text = budget_text
            changed = True
        if self._story != story:
            self._story = story
            changed = True
        if changed:
            self.projectMetaChanged.emit()

    @Slot(str)
    def select_project(self, project_name: str):
        self.set_selected_project(project_name)

    @Slot(str)
    def edit_project(self, project_name: str):
        self.requestEditProject.emit(project_name)

    @Slot(str)
    def create_project(self, project_name: str):
        self.requestCreateProject.emit(project_name)

    @Slot()
    def refresh_projects(self):
        self.requestRefreshProjects.emit()

    @Slot()
    def close_window(self):
        self.requestCloseWindow.emit()

    @Slot()
    def open_settings(self):
        self.requestOpenSettings.emit()

    @Slot()
    def open_server_dialog(self):
        self.requestOpenServerDialog.emit()

    @Slot(str)
    def set_active_panel(self, panel_name: str):
        panel_name = panel_name or "members"
        if self._active_panel != panel_name:
            self._active_panel = panel_name
            self.activePanelChanged.emit()
            self.activePanelTitleChanged.emit()

    def set_member_items(self, items):
        self._member_items = items or []
        self.memberItemsChanged.emit()

    def set_screenplay_data(self, *, summary: str, items):
        self._screenplay_summary = summary or ""
        self._screenplay_items = items or []
        self.screenplaySummaryChanged.emit()
        self.screenplayItemsChanged.emit()


class StartupWindow(QDialog):
    enter_edit_mode = Signal(str)

    def __init__(self, workspace: Workspace):
        super().__init__(parent=None)
        self.workspace = workspace
        self._pending_prompt = None
        self._window_sizes = {}
        self._load_window_sizes()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("startup_window_qml")

        self._bridge = _StartupWindowBridge(self)
        self._bridge.requestEditProject.connect(self._on_edit_project)
        self._bridge.requestCreateProject.connect(self._on_create_project)
        self._bridge.requestRefreshProjects.connect(self.refresh_projects)
        self._bridge.requestCloseWindow.connect(self.close)
        self._bridge.requestOpenSettings.connect(self._on_settings_clicked)
        self._bridge.requestOpenServerDialog.connect(self._on_server_status_clicked)
        self._bridge.selectedProjectChanged.connect(self._refresh_selected_project_meta)
        self._bridge.activePanelChanged.connect(self._on_active_panel_changed)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)
        self._quick.rootContext().setContextProperty("startupBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(STARTUP_QML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

        width, height = self._get_window_size()
        self.resize(width, height)
        self.setWindowState(Qt.WindowNoState)
        screen = self.screen().availableGeometry()
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)

        self.refresh_projects()
        self._startup_panel_switcher = None

    def _load_window_sizes(self):
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    self._window_sizes = json.load(f)
            else:
                self._window_sizes = {"startup": {"width": 1600, "height": 900}}
        except Exception as e:
            logger.error("Error loading window sizes: %s", e)
            self._window_sizes = {"startup": {"width": 1600, "height": 900}}

    def _save_window_sizes(self):
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "window_sizes.json")
            existing_sizes = {}
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    existing_sizes = json.load(f)
            existing_sizes["startup"] = {"width": self.width(), "height": self.height()}
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(existing_sizes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving window sizes: %s", e)

    def _get_window_size(self):
        stored = (self._window_sizes or {}).get("startup", {})
        return int(stored.get("width", 1600)), int(stored.get("height", 900))

    def closeEvent(self, event):
        self._save_window_sizes()
        QApplication.instance().quit()
        event.accept()

    def _on_edit_project(self, project_name: str):
        if not project_name:
            return
        self.workspace.switch_project(project_name)
        self.enter_edit_mode.emit(project_name)

    def _on_create_project(self, project_name: str):
        name = (project_name or "").strip()
        if not name:
            return
        try:
            self.workspace.project_manager.create_project(name)
            self.refresh_projects()
            self._bridge.set_selected_project(name)
        except Exception as e:
            logger.error("Error creating project: %s", e)

    def refresh_projects(self):
        self.workspace.project_manager.ensure_projects_loaded()
        projects = self.workspace.project_manager.list_projects()
        self._bridge.set_projects([{"name": p} for p in projects])
        if projects and self._bridge.selectedProject not in projects:
            self._bridge.set_selected_project(projects[0])
        self._refresh_selected_project_meta()

    def _refresh_selected_project_meta(self):
        project_name = self._bridge.selectedProject
        if not project_name:
            self._bridge.set_project_meta(
                timeline_count="0",
                task_count="0",
                budget_text="$0.00 / $0.00",
                story="",
            )
            return
        project = self.workspace.project_manager.get_project(project_name)
        if not project:
            return
        config = project.get_config()
        timeline_count = str(config.get("timeline_index", 0))
        task_count = str(config.get("task_index", 0))
        used = float(config.get("budget_used", 0) or 0)
        total = float(config.get("budget_total", 0) or 0)
        budget_text = f"${used:.2f} / ${total:.2f}"
        story = config.get("story_description", "") or ""
        self._bridge.set_project_meta(
            timeline_count=timeline_count,
            task_count=task_count,
            budget_text=budget_text,
            story=story,
        )
        self._refresh_member_items_for_project(project_name)
        self._refresh_screenplay_items_for_project(project_name)
        self._sync_startup_panel_project(project_name)

    def _refresh_member_items_for_project(self, project_name: str):
        if not project_name:
            self._bridge.set_member_items([])
            return
        try:
            project = self.workspace.project_manager.get_project(project_name)
            if not project:
                self._bridge.set_member_items([])
                return
            from agent.crew import CrewService
            crew_service = CrewService()
            members = crew_service.list_crew_members(project)
            rows = []
            for m in members:
                rows.append(
                    {
                        "name": getattr(getattr(m, "config", None), "name", "") or "",
                        "icon": getattr(getattr(m, "config", None), "icon", "") or "",
                        "color": getattr(getattr(m, "config", None), "color", "#5c5f66") or "#5c5f66",
                    }
                )
            self._bridge.set_member_items(rows)
        except Exception as e:
            logger.debug("Failed to refresh member items: %s", e)
            self._bridge.set_member_items([])

    def _refresh_screenplay_items_for_project(self, project_name: str):
        if not project_name:
            self._bridge.set_screenplay_data(summary="", items=[])
            return
        try:
            project = self.workspace.project_manager.get_project(project_name)
            if not project:
                self._bridge.set_screenplay_data(summary="", items=[])
                return
            manager = project.get_screenplay_manager()
            scenes = manager.list_scenes() if manager else []
            scenes.sort(key=lambda s: str(getattr(s, "scene_number", "")))
            rows = []
            for scene in scenes[:20]:
                rows.append(
                    {
                        "sceneNumber": str(getattr(scene, "scene_number", "") or ""),
                        "title": str(getattr(scene, "title", "") or ""),
                        "overview": str(getattr(scene, "logline", "") or getattr(scene, "story_beat", "") or ""),
                    }
                )
            summary = f"{len(scenes)} scenes"
            self._bridge.set_screenplay_data(summary=summary, items=rows)
        except Exception as e:
            logger.debug("Failed to refresh screenplay items: %s", e)
            self._bridge.set_screenplay_data(summary="", items=[])

    def get_selected_project(self) -> str:
        return self._bridge.selectedProject

    def _ensure_startup_panel_switcher(self):
        if self._startup_panel_switcher:
            return
        from app.ui.window.startup.panel_switcher import StartupWindowWorkspaceTopRightBar
        self._startup_panel_switcher = StartupWindowWorkspaceTopRightBar(self.workspace, self)

    def _sync_startup_panel_project(self, project_name: str):
        if not project_name:
            return
        try:
            self.workspace.switch_project(project_name)
        except Exception as e:
            logger.debug("Project sync failed for panel switcher: %s", e)

    def _on_active_panel_changed(self):
        panel = self._bridge.activePanel
        if not panel:
            return
        try:
            self._ensure_startup_panel_switcher()
            selected = self._bridge.selectedProject
            if selected:
                self._sync_startup_panel_project(selected)
            self._startup_panel_switcher.switch_to_panel(panel)
        except Exception as e:
            logger.error("Failed to switch startup panel '%s': %s", panel, e)

    def _on_settings_clicked(self):
        from app.ui.settings import SettingsWidget

        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Settings")
        settings_dialog.setMinimumSize(900, 700)
        settings_dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        layout = QVBoxLayout(settings_dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        settings_widget = SettingsWidget(self.workspace)
        layout.addWidget(settings_widget)
        settings_dialog.exec()

    def _on_server_status_clicked(self):
        from app.ui.server_status import ServerListDialog

        server_dialog = ServerListDialog(self.workspace, self)
        server_dialog.servers_modified.connect(self.refresh_projects)
        server_dialog.exec()

