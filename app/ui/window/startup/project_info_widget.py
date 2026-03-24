from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.i18n_utils import tr

PROJECT_INFO_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "ProjectInfoWidget.qml"

class _ProjectInfoBridge(QObject):
    editRequested = Signal(str)
    projectNameChanged = Signal()
    timelineCountChanged = Signal()
    taskCountChanged = Signal()
    budgetTextChanged = Signal()
    budgetPercentChanged = Signal()
    storyDescriptionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_name = ""
        self._timeline_count = "0"
        self._task_count = "0"
        self._budget_text = "$0.00 / $0.00"
        self._budget_percent = 0
        self._story = ""

    @Property(str, notify=projectNameChanged)
    def projectName(self):
        return self._project_name

    @Property(str, constant=True)
    def videoText(self):
        return tr("No Video Preview")

    @Property(str, constant=True)
    def editLabel(self):
        return tr("Edit")

    @Property(str, constant=True)
    def timelineLabel(self):
        return tr("Timeline Items")

    @Property(str, constant=True)
    def taskLabel(self):
        return tr("Task Count")

    @Property(str, constant=True)
    def budgetLabel(self):
        return tr("Budget Usage")

    @Property(str, constant=True)
    def storyLabel(self):
        return tr("Story Description")

    @Property(str, notify=timelineCountChanged)
    def timelineCount(self):
        return self._timeline_count

    @Property(str, notify=taskCountChanged)
    def taskCount(self):
        return self._task_count

    @Property(str, notify=budgetTextChanged)
    def budgetText(self):
        return self._budget_text

    @Property(int, notify=budgetPercentChanged)
    def budgetPercent(self):
        return self._budget_percent

    @Property(str, notify=storyDescriptionChanged)
    def storyDescription(self):
        return self._story

    def set_data(self, *, name: str, timeline: str, task: str, budget_text: str, budget_percent: int, story: str):
        if self._project_name != name:
            self._project_name = name
            self.projectNameChanged.emit()
        if self._timeline_count != timeline:
            self._timeline_count = timeline
            self.timelineCountChanged.emit()
        if self._task_count != task:
            self._task_count = task
            self.taskCountChanged.emit()
        if self._budget_text != budget_text:
            self._budget_text = budget_text
            self.budgetTextChanged.emit()
        if self._budget_percent != budget_percent:
            self._budget_percent = budget_percent
            self.budgetPercentChanged.emit()
        if self._story != story:
            self._story = story
            self.storyDescriptionChanged.emit()

    @Slot()
    def request_edit(self):
        if self._project_name:
            self.editRequested.emit(self._project_name)


class ProjectInfoWidget(BaseWidget):
    edit_project = Signal(str)

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.setObjectName("project_info_widget")
        self._current_project_name = None
        self._bridge = _ProjectInfoBridge(self)
        self._bridge.editRequested.connect(self.edit_project.emit)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)
        self._quick.rootContext().setContextProperty("projectInfoBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(PROJECT_INFO_QML_PATH)))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._quick)

    def set_project(self, project_name: str):
        self._current_project_name = project_name
        if not project_name:
            self._bridge.set_data(
                name="",
                timeline="0",
                task="0",
                budget_text="$0.00 / $0.00",
                budget_percent=0,
                story="",
            )
            return

        project = self.workspace.project_manager.get_project(project_name)
        if project:
            config = project.get_config()
            timeline_count = config.get('timeline_index', 0)
            task_count = config.get('task_index', 0)
            budget_used = config.get('budget_used', 0)
            budget_total = config.get('budget_total', 100)
            budget_percent = int((budget_used / budget_total) * 100) if budget_total else 0
            story = config.get('story_description', '')
            self._bridge.set_data(
                name=project_name,
                timeline=str(timeline_count),
                task=str(task_count),
                budget_text=f"${budget_used:.2f} / ${budget_total:.2f}",
                budget_percent=budget_percent,
                story=story,
            )
