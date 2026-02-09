"""Agent chat plan widget for showing active execution plan."""

from typing import Dict, Optional, Tuple, List
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QSize

from agent import AgentMessage
from app.ui.base_widget import BaseWidget
from agent.plan.plan_service import PlanService
from agent.plan.plan_models import Plan, PlanInstance, PlanStatus, PlanTask, TaskStatus
from agent.crew.crew_service import CrewService
from agent.plan.plan_signals import plan_signal_manager
from utils.i18n_utils import tr

from .plan_clickable_frame import ClickableFrame
from .plan_status_icon import StatusIconWidget
from .plan_status_count import StatusCountWidget
from .plan_task_row import PlanTaskRow


class AgentChatPlanWidget(BaseWidget):
    """Plan widget embedded in agent chat."""

    def __init__(self, workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Get PlanService instance - will use default project name
        project_name = getattr(workspace, 'get_project', lambda: None)()
        project_name = project_name.project_name if project_name else "default"
        self.plan_service = PlanService.get_instance(workspace, project_name)
        self.crew_service = CrewService()

        self._crew_member_metadata: Dict[str, object] = {}
        self._preferred_plan_id: Optional[str] = None
        self._current_plan_id: Optional[str] = None
        self._is_expanded = False
        self._details_max_height = 220

        # Fixed heights for collapsed and expanded states
        self.header_height = 40  # Fixed height of the header (matches collapsed height)
        self._collapsed_height = 40  # Height when collapsed (just header)
        self._expanded_height = 260  # Height when expanded (header + details)

        # Create a vertical splitter to separate header and details
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setObjectName("plan_main_splitter")

        # Create header frame
        self.header_frame = ClickableFrame()
        self.header_frame.setObjectName("plan_header")
        self.header_frame.setCursor(Qt.PointingHandCursor)
        self.header_frame.clicked.connect(self.toggle_expanded)
        self.header_frame.setFixedHeight(self.header_height)
        self.header_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Create details container (initially hidden when collapsed)
        self.details_container = QWidget()
        self.details_container.setObjectName("plan_details_container")

        # Add header and details to the splitter
        self.main_splitter.addWidget(self.header_frame)
        self.main_splitter.addWidget(self.details_container)

        # Set up the main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.main_splitter)

        # Set up UI components first
        self._setup_ui()
        self._load_crew_member_metadata()

        # Configure the splitter - initially only show header
        # Set the correct size policy to ensure proper sizing in parent splitter
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Set the fixed height to match the header height when collapsed
        self.setFixedHeight(self.header_height)

        # Use QTimer.singleShot to ensure this happens after the layout is set up
        from PySide6.QtCore import QTimer
        def set_initial_splitter_sizes():
            self.main_splitter.setSizes([self.header_height, 0])  # Initially hide details

        QTimer.singleShot(0, set_initial_splitter_sizes)

        # Delay the initial refresh until after the constructor completes
        QTimer.singleShot(0, self.refresh_plan)

        # Connect to global plan signals instead of using timer
        plan_signal_manager.plan_created.connect(self._on_plan_change)
        plan_signal_manager.plan_updated.connect(self._on_plan_change)
        plan_signal_manager.plan_instance_created.connect(self._on_plan_change)
        plan_signal_manager.plan_instance_status_updated.connect(self._on_plan_change)
        plan_signal_manager.task_status_updated.connect(self._on_plan_change)

    def _setup_ui(self):
        from app.ui.components.avatar_widget import AvatarWidget

        self.setObjectName("agent_chat_plan_widget")
        self.setStyleSheet("""
            QWidget#agent_chat_plan_widget {
                background-color: #252525;
                border-radius: 6px;
            }
            QFrame#plan_header {
                background-color: #2b2d30;
                border-radius: 6px;
            }
            QLabel#plan_summary {
                color: #e1e1e1;
                font-size: 13px;
            }
            QWidget#plan_details_container {
                background-color: #252525;
                border-left: 1px solid #3a3a3a;
                border-right: 1px solid #3a3a3a;
                border-bottom: 1px solid #3a3a3a;
                border-radius: 0 0 6px 6px; /* Rounded bottom corners only */
            }
            QScrollArea#plan_details_scroll {
                background-color: #252525;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2b2d30;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #505254;
                min-height: 20px;
                border-radius: 4px;
            }
        """)

        # Setup header layout
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(8, 8, 8, 8)  # Add padding inside the header
        header_layout.setSpacing(8)

        self.plan_icon = AvatarWidget(icon="P", color="#4080ff", size=20, shape="circle", parent=self.header_frame)
        header_layout.addWidget(self.plan_icon, 0, Qt.AlignVCenter)

        self.summary_label = QLabel(tr("No active plan"), self.header_frame)
        self.summary_label.setObjectName("plan_summary")
        self.summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout.addWidget(self.summary_label, 1)

        self.status_container = QWidget(self.header_frame)
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self.running_count = StatusCountWidget("R", "#f4c542", tr("Running"), parent=self.status_container)
        self.waiting_count = StatusCountWidget("W", "#3498db", tr("Waiting"), parent=self.status_container)
        self.success_count = StatusCountWidget("S", "#2ecc71", tr("Success"), parent=self.status_container)
        self.failed_count = StatusCountWidget("F", "#e74c3c", tr("Failed"), parent=self.status_container)

        status_layout.addWidget(self.running_count)
        status_layout.addWidget(self.waiting_count)
        status_layout.addWidget(self.success_count)
        status_layout.addWidget(self.failed_count)

        header_layout.addWidget(self.status_container, 0, Qt.AlignVCenter)

        # Setup details container layout
        details_layout = QVBoxLayout(self.details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0)

        self.details_scroll = QScrollArea()
        self.details_scroll.setObjectName("plan_details_scroll")
        self.details_scroll.setWidgetResizable(True)
        self.details_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.details_scroll.setMaximumHeight(self._details_max_height)

        self.details_content_widget = QWidget()
        self.details_content_widget.setObjectName("plan_details_content_widget")
        self.details_layout = QVBoxLayout(self.details_content_widget)
        self.details_layout.setContentsMargins(6, 6, 6, 6)
        self.details_layout.setSpacing(6)

        self.empty_label = QLabel(tr("No tasks available"), self.details_content_widget)
        self.empty_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
        self.details_layout.addWidget(self.empty_label)

        self.details_scroll.setWidget(self.details_content_widget)
        details_layout.addWidget(self.details_scroll)

    def on_project_switched(self, project_name: str):
        self._preferred_plan_id = None
        self._current_plan_id = None
        self._load_crew_member_metadata()
        self.refresh_plan()

    def has_tasks(self):
        """Check if there are any tasks to display."""
        project_name = self._get_project_name()
        if not project_name:
            return False

        plan, instance = self._resolve_active_plan(project_name)

        tasks = []
        if instance:
            tasks = instance.tasks
        elif plan:
            tasks = plan.tasks

        return bool(tasks)

    def toggle_expanded(self):
        # Only toggle if there are tasks to show
        if not self.has_tasks():
            return

        self._is_expanded = not self._is_expanded

        # Update border radius based on expanded state
        if self._is_expanded:
            # When expanded, header has only top corners rounded
            self.header_frame.setStyleSheet("""
                QFrame#plan_header {
                    background-color: #2b2d30;
                    border-radius: 6px 6px 0 0;
                }
            """)
        else:
            # When collapsed, header has full border radius
            self.header_frame.setStyleSheet("""
                QFrame#plan_header {
                    background-color: #2b2d30;
                    border-radius: 6px;
                }
            """)

        # Update the splitter sizes based on expanded state
        if self._is_expanded:
            # Show both header and details
            self.main_splitter.setSizes([self.header_height, self._details_max_height])
            # Make sure the entire widget can expand
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # Remove fixed height constraint when expanded
            self.setMaximumHeight(16777215)  # Reset to default max
        else:
            # Show only header, hide details
            self.main_splitter.setSizes([self.header_height, 0])
            # Set fixed height policy to ensure the widget doesn't request more space
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # If this widget is inside a parent splitter, adjust the height accordingly
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'QSplitter':
                # Get the index of this widget in the splitter
                index = parent.indexOf(self)
                if index != -1:
                    sizes = parent.sizes()
                    if self._is_expanded:
                        # Use fixed expanded height
                        sizes[index] = self._expanded_height
                    else:
                        # Use fixed collapsed height
                        sizes[index] = self._collapsed_height
                    parent.setSizes(sizes)
                    # Force the splitter to update its layout
                    parent.update()
                break
            parent = parent.parent()

        # Update the geometry of this widget
        self.updateGeometry()

        # In collapsed state, ensure the widget doesn't request more space than allocated
        if not self._is_expanded:
            # Make sure the widget respects the parent's allocation
            self.setMinimumHeight(self.header_height)
            self.setMaximumHeight(self.header_height)
        else:
            # Reset height constraints when expanded
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)  # Default maximum

    async def handle_agent_message(self, message: AgentMessage):
        """Handle an AgentMessage directly."""
        if not message:
            return

        # Check if this message contains plan update information
        if message.metadata:
            event_type = message.metadata.get("event_type", "")
            if event_type == "plan_update":
                plan_id = message.metadata.get("plan_id")
                if plan_id:
                    self._preferred_plan_id = plan_id
                self.refresh_plan()

        # Check message content for plan-related information
        if message.content and "plan" in message.content.lower():
            self.refresh_plan()

        # Check structured_content for plan-related types
        if hasattr(message, 'structured_content') and message.structured_content:
            from agent.chat.agent_chat_types import ContentType
            for content in message.structured_content:
                if hasattr(content, 'content_type'):
                    content_type_str = str(content.content_type).lower()
                    if content_type_str == "plan" or "plan" in content_type_str:
                        self.refresh_plan()
                        break

        # Process UI updates to ensure changes are reflected
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def handle_stream_event(self, event, _session=None):
        if not event:
            return
        if event.event_type == "plan_update":
            plan_id = event.data.get("plan_id") if event.data else None
            if plan_id:
                self._preferred_plan_id = plan_id
            self.refresh_plan()

    def refresh_plan(self):
        project_name = self._get_project_name()
        if not project_name:
            self._set_no_plan()
            return

        plan, instance = self._resolve_active_plan(project_name)
        self._update_summary(plan, instance)
        self._update_task_list(plan, instance)

        # Update the current plan ID to the one we just loaded
        if plan:
            self._current_plan_id = plan.id

    def _get_project_name(self) -> Optional[str]:
        project = self.workspace.get_project() if self.workspace else None
        if not project:
            return None
        if hasattr(project, "project_name"):
            return project.project_name
        if hasattr(project, "name"):
            return project.name
        if isinstance(project, str):
            return project
        return None

    def _resolve_active_plan(self, project_name: str) -> Tuple[Optional[Plan], Optional[PlanInstance]]:
        active_statuses = {PlanStatus.RUNNING, PlanStatus.CREATED, PlanStatus.PAUSED}

        if self._preferred_plan_id:
            plan = self.plan_service.load_plan(project_name, self._preferred_plan_id)
            if plan:
                instance = self._load_latest_instance(project_name, plan.id)
                if instance and instance.status in active_statuses:
                    return plan, instance
                return plan, instance

        # First, try to find active plans
        candidates: List[Tuple[Plan, PlanInstance]] = []
        plans = self.plan_service.get_all_plans_for_project(project_name)
        for plan in plans:
            instance = self._load_latest_instance(project_name, plan.id)
            if instance and instance.status in active_statuses:
                candidates.append((plan, instance))

        if candidates:
            # Return the most recent active plan
            return max(candidates, key=lambda item: self._instance_sort_key(item[1]))

        # If no active plans, look for the most recent plan regardless of status
        all_candidates: List[Tuple[Plan, PlanInstance]] = []
        for plan in plans:
            instance = self._load_latest_instance(project_name, plan.id)
            if instance:
                all_candidates.append((plan, instance))

        if all_candidates:
            # Return the most recent plan regardless of status
            return max(all_candidates, key=lambda item: self._instance_sort_key(item[1]))

        return None, None

    def _load_latest_instance(self, project_name: str, plan_id: str) -> Optional[PlanInstance]:
        instances = self.plan_service.get_all_instances_for_plan(project_name, plan_id)
        if not instances:
            return None
        return max(instances, key=self._instance_sort_key)

    def _instance_sort_key(self, instance: PlanInstance) -> datetime:
        return instance.started_at or instance.created_at or datetime.min

    def _update_summary(self, plan: Optional[Plan], instance: Optional[PlanInstance]):
        if not plan:
            self.summary_label.setText(tr("No active plan"))
            self.summary_label.setToolTip("")
            self._set_counts(0, 0, 0, 0)
            return

        tasks = instance.tasks if instance else plan.tasks
        running, waiting, success, failed = self._count_task_status(tasks)
        self._set_counts(running, waiting, success, failed)

        summary_text = self._build_summary_text(plan, tasks)
        self.summary_label.setText(summary_text)
        self.summary_label.setToolTip(plan.description or summary_text)

    def _build_summary_text(self, plan: Plan, tasks: List[PlanTask]) -> str:
        running = [t for t in tasks if t.status == TaskStatus.RUNNING]
        waiting = [t for t in tasks if t.status in {TaskStatus.CREATED, TaskStatus.READY}]
        if running:
            task_text = running[0].name or running[0].description or tr("Running task")
            return f"{tr('Running')}: {self._truncate_text(task_text, 80)}"
        if waiting:
            task_text = waiting[0].name or waiting[0].description or tr("Waiting task")
            return f"{tr('Waiting')}: {self._truncate_text(task_text, 80)}"
        if plan.name:
            return self._truncate_text(plan.name, 80)
        if plan.description:
            return self._truncate_text(plan.description, 80)
        return tr("Plan in progress")

    def _truncate_text(self, text: str, limit: int) -> str:
        if text is None:
            return ""
        cleaned = text.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(0, limit - 3)].rstrip() + "..."

    def _count_task_status(self, tasks: List[PlanTask]) -> Tuple[int, int, int, int]:
        running = 0
        waiting = 0
        success = 0
        failed = 0
        for task in tasks:
            if task.status == TaskStatus.RUNNING:
                running += 1
            elif task.status in {TaskStatus.CREATED, TaskStatus.READY}:
                waiting += 1
            elif task.status == TaskStatus.COMPLETED:
                success += 1
            elif task.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
                failed += 1
        return running, waiting, success, failed

    def _set_counts(self, running: int, waiting: int, success: int, failed: int):
        self.running_count.set_count(running)
        self.waiting_count.set_count(waiting)
        self.success_count.set_count(success)
        self.failed_count.set_count(failed)

    def _update_task_list(self, plan: Optional[Plan], instance: Optional[PlanInstance]):
        self._clear_layout(self.details_layout)

        tasks = []
        if instance:
            tasks = instance.tasks
        elif plan:
            tasks = plan.tasks

        if not tasks:
            self.empty_label = QLabel(tr("No tasks available"), self.details_content_widget)
            self.empty_label.setStyleSheet("color: #9a9a9a; font-size: 12px;")
            self.details_layout.addWidget(self.empty_label)
            self._update_details_height()
            return

        for task in tasks:
            status_label, status_color = self._status_style(task.status)
            crew_member = self._find_crew_member(task.title)
            row = PlanTaskRow(task, crew_member, status_label, status_color, parent=self.details_content_widget)
            self.details_layout.addWidget(row)

        self.details_layout.addStretch()
        self._update_details_height()

    def _status_style(self, status: TaskStatus) -> Tuple[str, str]:
        if status == TaskStatus.RUNNING:
            return "R", "#f4c542"
        if status in {TaskStatus.CREATED, TaskStatus.READY}:
            return "W", "#3498db"
        if status == TaskStatus.COMPLETED:
            return "S", "#2ecc71"
        return "F", "#e74c3c"

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _set_no_plan(self):
        self.summary_label.setText(tr("No active plan"))
        self.summary_label.setToolTip("")
        self._set_counts(0, 0, 0, 0)
        self._update_task_list(None, None)

    def _load_crew_member_metadata(self):
        try:
            project = self.workspace.get_project() if self.workspace else None
            if not project:
                self._crew_member_metadata = {}
                return

            crew_members = self.crew_service.get_project_crew_members(project)
            self._crew_member_metadata = {}
            for name, crew_member in crew_members.items():
                if not crew_member or not crew_member.config:
                    continue
                self._crew_member_metadata[name.lower()] = crew_member
                crew_title = crew_member.config.metadata.get("crew_title") if crew_member.config.metadata else None
                if crew_title:
                    self._crew_member_metadata[crew_title.lower()] = crew_member
        except Exception:
            self._crew_member_metadata = {}

    def _find_crew_member(self, title: Optional[str]):
        if not title:
            return None
        if not self._crew_member_metadata:
            self._load_crew_member_metadata()
        return self._crew_member_metadata.get(title.lower())

    def _on_plan_change(self, *args):
        """Callback for when plan-related changes occur."""
        # Refresh the plan display when any plan-related change happens
        # Use singleShot to avoid multiple rapid updates
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.refresh_plan)

    def _update_details_height(self):
        if not self.details_scroll:
            return
        # Only update the details height if the widget is expanded
        # This prevents changes during refresh_plan from affecting the collapsed state
        if self._is_expanded:
            content_height = self.details_content_widget.sizeHint().height()
            target_height = min(self._details_max_height, max(0, content_height))
            # Update the splitter instead of setting fixed height on scroll area
            self.main_splitter.setSizes([self.header_height, target_height])

    def sizeHint(self):
        """Return the recommended size for this widget."""
        hint = super().sizeHint()
        if hasattr(self, '_is_expanded') and not self._is_expanded:
            # When collapsed, return the collapsed height
            return QSize(hint.width(), self._collapsed_height)
        else:
            # When expanded, return normal size hint
            return hint

    def __del__(self):
        """Disconnect signals when the widget is destroyed."""
        try:
            plan_signal_manager.plan_created.disconnect(self._on_plan_change)
            plan_signal_manager.plan_updated.disconnect(self._on_plan_change)
            plan_signal_manager.plan_instance_created.disconnect(self._on_plan_change)
            plan_signal_manager.plan_instance_status_updated.disconnect(self._on_plan_change)
            plan_signal_manager.task_status_updated.disconnect(self._on_plan_change)
        except TypeError:
            # Signals may already be disconnected
            pass
