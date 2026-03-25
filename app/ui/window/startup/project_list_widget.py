import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
from PySide6.QtGui import QColor

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)
PROJECT_LIST_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "ProjectListWidget.qml"


class _ProjectListBridge(QObject):
    projectsChanged = Signal()
    selectedProjectChanged = Signal()
    projectSelected = Signal(str)
    projectEdit = Signal(str)
    createProjectRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects = []
        self._selected_project = ""

    @Property("QVariantList", notify=projectsChanged)
    def projects(self):
        return self._projects

    @Property(str, notify=selectedProjectChanged)
    def selectedProject(self):
        return self._selected_project

    def set_projects(self, projects):
        self._projects = projects
        self.projectsChanged.emit()

    def set_selected_project(self, name: str):
        name = name or ""
        if self._selected_project != name:
            self._selected_project = name
            self.selectedProjectChanged.emit()

    @Slot(str)
    def select_project(self, name: str):
        self.set_selected_project(name)
        self.projectSelected.emit(name)

    @Slot(str)
    def request_edit(self, name: str):
        self.projectEdit.emit(name)

    @Slot()
    def request_create_project(self):
        self.createProjectRequested.emit()


class ProjectListWidget(BaseWidget):
    project_selected = Signal(str)
    project_edit = Signal(str)
    project_created = Signal(str)

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.setObjectName("project_list_widget")
        self._selected_project = None

        self._bridge = _ProjectListBridge(self)
        self._bridge.projectSelected.connect(self._select_project)
        self._bridge.projectEdit.connect(self._on_project_edit)
        self._bridge.createProjectRequested.connect(self._on_add_project)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        # Make the QML surface opaque; otherwise the startup project's list panel
        # becomes see-through because the QML root also uses transparent colors.
        self._quick.setAttribute(Qt.WA_TranslucentBackground, False)
        self._quick.setClearColor(QColor("#2b2d30"))
        qml_root_dir = Path(__file__).resolve().parent.parent.parent / "qml"
        self._quick.engine().addImportPath(str(qml_root_dir))
        self._quick.rootContext().setContextProperty("projectListBridge", self._bridge)
        self._quick.statusChanged.connect(self._on_qml_status_changed)
        self._quick.setSource(QUrl.fromLocalFile(str(PROJECT_LIST_QML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

        self._load_projects()

    @Slot(int)
    def _on_qml_status_changed(self, _status: int):
        if self._quick.status() != QQuickWidget.Error:
            return
        errors = [e.toString() for e in self._quick.errors()]
        logger.error("ProjectListWidget QML load error: %s", "; ".join(errors))

    def _load_projects(self):
        self.workspace.project_manager.ensure_projects_loaded()
        project_names = self.workspace.project_manager.list_projects()
        self._bridge.set_projects([{"name": n} for n in project_names])
        if project_names:
            self._select_project(project_names[0])

    def _select_project(self, project_name: str):
        self._selected_project = project_name
        self._bridge.set_selected_project(project_name)
        self.project_selected.emit(project_name)

    def _on_project_edit(self, project_name: str):
        self.project_edit.emit(project_name)

    def _on_add_project(self):
        from app.ui.dialog.custom_dialog import CustomDialog

        dialog = CustomDialog(self)
        dialog.set_title(tr("新建项目"))

        content_layout = QVBoxLayout()
        label = QLabel(tr("请输入项目名称:"))
        label.setStyleSheet("color: #E1E1E1; font-size: 14px;")
        content_layout.addWidget(label)

        line_edit = QLineEdit()
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1f22;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 8px;
                color: #E1E1E1;
                selection-background-color: #4080ff;
                font-size: 14px;
            }
        """)
        content_layout.addWidget(line_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            dialog
        )
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #3d3f4e;
                color: #E1E1E1;
                border: 1px solid #505254;
                border-radius: 5px;
                padding: 6px 15px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #444654;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        content_layout.addWidget(button_box)

        dialog.setContentLayout(content_layout)
        line_edit.setFocus()

        if dialog.exec() == QDialog.Accepted:
            project_name = line_edit.text().strip()
            if project_name:
                try:
                    self.workspace.project_manager.create_project(project_name)
                    self._load_projects()
                    self._select_project(project_name)
                    self.project_created.emit(project_name)
                except Exception as e:
                    logger.error(f"Error creating project: {e}")

    def get_selected_project(self) -> str:
        return self._selected_project

    def refresh(self):
        self._load_projects()
