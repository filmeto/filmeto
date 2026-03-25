from PySide6.QtWidgets import QVBoxLayout

from app.data.workspace import Workspace
from app.ui.panels.base_panel import BasePanel
from app.ui.window.startup.project_info_widget import ProjectInfoWidget
from utils.i18n_utils import tr


class ProjectInfoPanel(BasePanel):
    """Startup right-side panel: project information summary."""

    def setup_ui(self):
        self.setObjectName("project_info_panel")
        self.set_panel_title(tr("Project"))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._info_widget = ProjectInfoWidget(self.workspace, self)
        layout.addWidget(self._info_widget)

        self.content_layout.addLayout(layout)

    def load_data(self):
        project = self.workspace.get_project()
        project_name = getattr(project, "project_name", None) if project else None
        self._info_widget.set_project(project_name or "")

    def on_project_switched(self, project_name: str):
        super().on_project_switched(project_name)
        self._info_widget.set_project(project_name or "")

    def set_project(self, project_name: str):
        self._info_widget.set_project(project_name or "")

