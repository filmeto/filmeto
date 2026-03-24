"""Canonical ViewModel module for chat plan QML."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

from agent.plan.plan_service import PlanService
from agent.plan.plan_models import Plan, PlanInstance, PlanStatus, PlanTask
from agent.plan.plan_signals import plan_signal_manager
from agent.crew.crew_service import CrewService
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class PlanViewModel(QObject):
    """Qt ViewModel for plan data exposure to QML."""

    planChanged = Signal(str, "QVariant")
    taskStatsChanged = Signal()
    taskUpdated = Signal(str, "QVariant")
    crewMembersChanged = Signal()
    resumeRequested = Signal(str)

    DEBOUNCE_INTERVAL = 50

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self._workspace = workspace
        self._plan_service: Optional[PlanService] = None
        self._crew_service = CrewService()

        self._project_name: str = ""
        self._preferred_plan_id: Optional[str] = None
        self._current_plan_id: Optional[str] = None
        self._crew_member_metadata: Dict[str, Any] = {}

        self._current_plan_data: Dict[str, Any] = {}
        self._tasks: List[Dict[str, Any]] = []
        self._running_count: int = 0
        self._waiting_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self.DEBOUNCE_INTERVAL)
        self._debounce_timer.timeout.connect(self._do_refresh)
        self._pending_refresh = False

        self._initialize()
        self._connect_signals()

    def _initialize(self):
        self._load_crew_member_metadata()
        self._update_project_name()

    def _connect_signals(self):
        plan_signal_manager.plan_created.connect(self._on_plan_created)
        plan_signal_manager.plan_updated.connect(self._on_plan_updated)
        plan_signal_manager.plan_deleted.connect(self._on_plan_deleted)
        plan_signal_manager.plan_instance_created.connect(self._on_plan_instance_created)
        plan_signal_manager.plan_instance_status_updated.connect(self._on_plan_instance_status_updated)
        plan_signal_manager.plan_task_updated.connect(self._on_plan_task_updated)

    def _update_project_name(self):
        project = self._workspace.get_project() if self._workspace else None
        if project:
            if hasattr(project, "project_name"):
                self._project_name = project.project_name
            elif hasattr(project, "name"):
                self._project_name = project.name
            elif isinstance(project, str):
                self._project_name = project
            self._plan_service = PlanService.get_instance(self._workspace, self._project_name)

    def _load_crew_member_metadata(self):
        try:
            project = self._workspace.get_project() if self._workspace else None
            if not project:
                self._crew_member_metadata = {}
                return

            crew_members = self._crew_service.get_project_crew_members(project)
            self._crew_member_metadata = {}
            for name, crew_member in crew_members.items():
                if not crew_member or not crew_member.config:
                    continue
                member_data = {
                    "name": crew_member.config.name or name,
                    "icon": crew_member.config.icon or "A",
                    "color": crew_member.config.color or "#5c5f66",
                    "title": crew_member.config.metadata.get("crew_title", "") if crew_member.config.metadata else "",
                }
                self._crew_member_metadata[name.lower()] = member_data
                if member_data["title"]:
                    self._crew_member_metadata[member_data["title"].lower()] = member_data
            self.crewMembersChanged.emit()
        except Exception as e:
            logger.error(f"Error loading crew member metadata: {e}")
            self._crew_member_metadata = {}

    def _get_crew_member(self, title: Optional[str]) -> Dict[str, Any]:
        if not title:
            return {"name": tr("Unknown"), "icon": "A", "color": "#5c5f66", "title": ""}
        if not self._crew_member_metadata:
            self._load_crew_member_metadata()
        return self._crew_member_metadata.get(
            title.lower(),
            {"name": title, "icon": "A", "color": "#5c5f66", "title": title},
        )

    def _on_plan_created(self, project_name: str, plan_id: str):
        if project_name != self._project_name:
            return
        self._preferred_plan_id = plan_id
        self._schedule_refresh()

    def _on_plan_updated(self, project_name: str, plan_id: str):
        if project_name != self._project_name:
            return
        if plan_id == self._current_plan_id or plan_id == self._preferred_plan_id:
            self._schedule_refresh()

    def _on_plan_deleted(self, project_name: str, plan_id: str):
        if project_name != self._project_name:
            return
        if self._preferred_plan_id == plan_id:
            self._preferred_plan_id = None
        self._schedule_refresh()

    def _on_plan_instance_created(self, project_name: str, plan_id: str, instance_id: str):
        if project_name != self._project_name:
            return
        self._schedule_refresh()

    def _on_plan_instance_status_updated(self, project_name: str, plan_id: str, instance_id: str):
        if project_name != self._project_name:
            return
        self._schedule_refresh()

    def _on_plan_task_updated(self, project_name: str, plan_id: str, instance_id: str, task_id: str):
        if project_name != self._project_name:
            return
        if plan_id != self._current_plan_id:
            self._schedule_refresh()
            return
        if self._try_incremental_task_update(task_id):
            return
        self._schedule_refresh()

    def _try_incremental_task_update(self, task_id: str) -> bool:
        if not self._plan_service or not self._current_plan_id:
            return False
        try:
            plan = self._plan_service.load_plan(self._project_name, self._current_plan_id)
            if not plan:
                return False
            instance = self._load_latest_instance(plan.id)
            tasks = instance.tasks if instance else plan.tasks
            for task in tasks:
                if task.id == task_id:
                    task_data = self._convert_task_to_dict(task)
                    for i, cached_task in enumerate(self._tasks):
                        if cached_task["id"] == task_id:
                            old_status = cached_task.get("status")
                            new_status = task_data["status"]
                            self._tasks[i] = task_data
                            if old_status != new_status:
                                self._adjust_status_count(old_status, -1)
                                self._adjust_status_count(new_status, 1)
                            self.taskUpdated.emit(task_id, task_data)
                            self.taskStatsChanged.emit()
                            return True
            return False
        except Exception as e:
            logger.error(f"Error in incremental task update: {e}")
            return False

    def _adjust_status_count(self, status: str, delta: int):
        if status == "running":
            self._running_count = max(0, self._running_count + delta)
        elif status in ("created", "ready"):
            self._waiting_count = max(0, self._waiting_count + delta)
        elif status == "completed":
            self._completed_count = max(0, self._completed_count + delta)
        elif status in ("failed", "cancelled"):
            self._failed_count = max(0, self._failed_count + delta)

    def _schedule_refresh(self):
        self._pending_refresh = True
        self._debounce_timer.start()

    def _do_refresh(self):
        if not self._pending_refresh:
            return
        self._pending_refresh = False
        self._refresh_plan_internal()

    @Slot()
    def refresh_plan(self):
        self._schedule_refresh()

    def _refresh_plan_internal(self):
        if not self._project_name or not self._plan_service:
            self._set_no_plan()
            return
        plan, instance = self._resolve_active_plan()
        self._update_plan_data(plan, instance)

    @Slot(str)
    def set_preferred_plan(self, plan_id: str):
        self._preferred_plan_id = plan_id if plan_id else None
        self._schedule_refresh()

    @Slot()
    def on_project_switched(self):
        self._preferred_plan_id = None
        self._current_plan_id = None
        self._update_project_name()
        self._load_crew_member_metadata()
        self._schedule_refresh()

    def _resolve_active_plan(self) -> tuple:
        active_statuses = {PlanStatus.RUNNING, PlanStatus.CREATED, PlanStatus.PAUSED}
        if self._preferred_plan_id:
            plan = self._plan_service.load_plan(self._project_name, self._preferred_plan_id)
            if plan:
                return plan, self._load_latest_instance(plan.id)
        candidates = []
        plans = self._plan_service.get_all_plans_for_project(self._project_name)
        for plan in plans:
            instance = self._load_latest_instance(plan.id)
            if instance and instance.status in active_statuses:
                candidates.append((plan, instance))
        if candidates:
            return max(candidates, key=lambda x: self._instance_sort_key(x[1]))
        all_candidates = []
        for plan in plans:
            instance = self._load_latest_instance(plan.id)
            if instance:
                all_candidates.append((plan, instance))
        if all_candidates:
            return max(all_candidates, key=lambda x: self._instance_sort_key(x[1]))
        return None, None

    def _load_latest_instance(self, plan_id: str) -> Optional[PlanInstance]:
        instances = self._plan_service.get_all_instances_for_plan(self._project_name, plan_id)
        if not instances:
            return None
        return max(instances, key=self._instance_sort_key)

    def _instance_sort_key(self, instance: PlanInstance) -> datetime:
        return instance.started_at or instance.created_at or datetime.min

    def _update_plan_data(self, plan: Optional[Plan], instance: Optional[PlanInstance]):
        if not plan:
            self._set_no_plan()
            return
        self._current_plan_id = plan.id
        tasks = instance.tasks if instance else plan.tasks
        effective_status = instance.status if instance else plan.status
        self._current_plan_data = {
            "plan_id": plan.id,
            "plan_name": plan.name or tr("Untitled Plan"),
            "plan_description": plan.description or "",
            "plan_status": effective_status.value if hasattr(effective_status, "value") else str(effective_status),
            "instance_id": instance.instance_id if instance else "",
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
        }
        self._tasks = []
        self._running_count = 0
        self._waiting_count = 0
        self._completed_count = 0
        self._failed_count = 0
        for task in tasks:
            task_data = self._convert_task_to_dict(task)
            self._tasks.append(task_data)
            status = task.status.value if hasattr(task.status, "value") else str(task.status)
            if status == "running":
                self._running_count += 1
            elif status in ("created", "ready"):
                self._waiting_count += 1
            elif status == "completed":
                self._completed_count += 1
            elif status in ("failed", "cancelled"):
                self._failed_count += 1
        self.planChanged.emit(plan.id, self._current_plan_data)
        self.taskStatsChanged.emit()

    def _set_no_plan(self):
        self._current_plan_id = None
        self._current_plan_data = {}
        self._tasks = []
        self._running_count = 0
        self._waiting_count = 0
        self._completed_count = 0
        self._failed_count = 0
        self.planChanged.emit("", {})
        self.taskStatsChanged.emit()

    def _convert_task_to_dict(self, task: PlanTask) -> Dict[str, Any]:
        crew_member = self._get_crew_member(task.title)
        return {
            "id": task.id,
            "name": task.name or task.description or tr("Untitled Task"),
            "description": task.description or "",
            "title": task.title or "",
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "crew_member": crew_member,
            "needs": task.needs or [],
            "error_message": task.error_message or "",
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    @Property(str, notify=planChanged)
    def planId(self) -> str:
        return self._current_plan_data.get("plan_id", "")

    @Property(str, notify=planChanged)
    def planName(self) -> str:
        return self._current_plan_data.get("plan_name", tr("No active plan"))

    @Property(str, notify=planChanged)
    def planDescription(self) -> str:
        return self._current_plan_data.get("plan_description", "")

    @Property(str, notify=planChanged)
    def planStatus(self) -> str:
        return self._current_plan_data.get("plan_status", "")

    @Property("QVariantList", notify=planChanged)
    def tasks(self) -> List[Dict[str, Any]]:
        return self._tasks

    @Property(int, notify=taskStatsChanged)
    def runningCount(self) -> int:
        return self._running_count

    @Property(int, notify=taskStatsChanged)
    def waitingCount(self) -> int:
        return self._waiting_count

    @Property(int, notify=taskStatsChanged)
    def completedCount(self) -> int:
        return self._completed_count

    @Property(int, notify=taskStatsChanged)
    def failedCount(self) -> int:
        return self._failed_count

    @Property(int, notify=taskStatsChanged)
    def totalTasks(self) -> int:
        return len(self._tasks)

    @Property(bool, notify=planChanged)
    def hasPlan(self) -> bool:
        return bool(self._current_plan_data)

    @Property(bool, notify=taskStatsChanged)
    def hasTasks(self) -> bool:
        return len(self._tasks) > 0

    @Property(str, notify=taskStatsChanged)
    def summaryText(self) -> str:
        if not self._tasks:
            return tr("No active plan")
        for task in self._tasks:
            if task.get("status") == "running":
                return f"{tr('Running')}: {self._truncate_text(task.get('name', tr('Running task')), 60)}"
        for task in self._tasks:
            if task.get("status") in ("created", "ready"):
                return f"{tr('Waiting')}: {self._truncate_text(task.get('name', tr('Waiting task')), 60)}"
        if self._current_plan_data.get("plan_name"):
            return self._truncate_text(self._current_plan_data["plan_name"], 80)
        return tr("Plan in progress")

    def _truncate_text(self, text: str, limit: int) -> str:
        if not text:
            return ""
        text = text.strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)].rstrip() + "..."

    @Property(bool, notify=planChanged)
    def isPaused(self) -> bool:
        return self._current_plan_data.get("plan_status") == "paused"

    @Property(bool, notify=planChanged)
    def canResume(self) -> bool:
        if not self._current_plan_data or self._current_plan_data.get("plan_status") != "paused":
            return False
        for task in self._tasks:
            if task.get("status") in ("created", "ready"):
                return True
        return False

    @Property(str, notify=planChanged)
    def pausedReason(self) -> str:
        if self._current_plan_data.get("plan_status") != "paused":
            return ""
        return tr("Plan was interrupted. Click to resume.")

    @Slot()
    def checkInterruptedPlans(self):
        if not self._plan_service or not self._project_name:
            return
        try:
            paused_instances = self._plan_service.mark_interrupted_as_paused(self._project_name)
            if paused_instances:
                logger.info(f"Marked {len(paused_instances)} interrupted plans as PAUSED")
                self._schedule_refresh()
        except Exception as e:
            logger.error(f"Error checking interrupted plans: {e}")

    @Slot(result=bool)
    def resumePlan(self) -> bool:
        if not self._plan_service or not self._project_name:
            return False
        try:
            resumable = self._plan_service.get_resumable_plan(self._project_name)
            if not resumable:
                logger.warning("No resumable plan found")
                return False
            plan, instance = resumable
            if not self._plan_service.resume_plan_instance(instance):
                logger.error(f"Failed to resume plan instance {instance.instance_id}")
                return False
            logger.info(f"Resumed plan {plan.id}, instance {instance.instance_id}")
            self._preferred_plan_id = plan.id
            self._schedule_refresh()
            return True
        except Exception as e:
            logger.error(f"Error resuming plan: {e}")
            return False

    @Slot()
    def requestResume(self):
        if self._current_plan_data:
            plan_id = self._current_plan_data.get("plan_id")
            if plan_id:
                self.resumeRequested.emit(plan_id)


# Backward compatibility alias
PlanBridge = PlanViewModel

__all__ = ["PlanViewModel", "PlanBridge"]
