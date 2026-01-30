import os
import json
import logging
import yaml
import tempfile
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict
from datetime import datetime
import shutil

from .plan_models import Plan, PlanInstance, PlanTask, PlanStatus, TaskStatus
from .plan_signals import plan_signal_manager

logger = logging.getLogger(__name__)


class PlanService:
    """
    Service for managing Plans and PlanInstances.

    Instances are managed statically and can be retrieved using get_instance().
    Each unique (workspace_path, project_name) combination gets its own instance.
    """

    # Class-level instance storage: dict[instance_key] -> PlanService
    _instances: Dict[str, 'PlanService'] = {}
    _lock = Lock()

    def __init__(self, workspace: Any = None, project_name: str = ""):
        """
        Initialize a PlanService instance.

        Args:
            workspace: The workspace object
            project_name: The name of the project
        """
        self.workspace = workspace
        self.project_name = project_name

        # Set up storage directory based on workspace
        if workspace and hasattr(workspace, 'workspace_path'):
            self.flow_storage_dir = Path(workspace.workspace_path) / "agent" / "plan" / "flow"
        else:
            # Default path for backward compatibility
            self.flow_storage_dir = Path("workspace/agent/plan/flow")
        self.flow_storage_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(
        cls,
        workspace: Any,
        project_name: str,
    ) -> 'PlanService':
        """
        Get or create a PlanService instance for the given workspace and project.

        Each unique (workspace_path, project_name) combination gets its own instance
        that will be reused across multiple calls.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            PlanService: The service instance for this workspace/project combination
        """
        # Extract workspace path for key generation
        workspace_path = cls._get_workspace_path(workspace)

        # Create instance key
        instance_key = f"{workspace_path}:{project_name}"

        # Check if instance already exists
        if instance_key in cls._instances:
            logger.debug(f"Reusing existing PlanService instance for {instance_key}")
            return cls._instances[instance_key]

        # Create new instance
        with cls._lock:
            # Double-check after acquiring lock
            if instance_key in cls._instances:
                return cls._instances[instance_key]

            logger.info(f"Creating new PlanService instance for {instance_key}")
            service = cls(workspace, project_name)

            # Store instance
            cls._instances[instance_key] = service
            return service

    @classmethod
    def remove_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Remove a PlanService instance from the cache.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            True if the instance was removed, False if it didn't exist
        """
        workspace_path = cls._get_workspace_path(workspace)
        instance_key = f"{workspace_path}:{project_name}"

        if instance_key in cls._instances:
            del cls._instances[instance_key]
            logger.info(f"Removed PlanService instance for {instance_key}")
            return True
        return False

    @classmethod
    def clear_all_instances(cls):
        """Clear all cached PlanService instances."""
        count = len(cls._instances)
        cls._instances.clear()
        logger.info(f"Cleared {count} PlanService instance(s)")

    @classmethod
    def list_instances(cls) -> List[str]:
        """
        List all cached instance keys.

        Returns:
            List of instance keys in format "workspace_path:project_name"
        """
        return list(cls._instances.keys())

    @classmethod
    def has_instance(cls, workspace: Any, project_name: str) -> bool:
        """
        Check if an instance exists for the given workspace and project.

        Args:
            workspace: The workspace object
            project_name: The name of the project

        Returns:
            True if an instance exists, False otherwise
        """
        workspace_path = cls._get_workspace_path(workspace)
        instance_key = f"{workspace_path}:{project_name}"
        return instance_key in cls._instances

    @staticmethod
    def _get_workspace_path(workspace: Any) -> str:
        """
        Extract workspace path from workspace object.

        Args:
            workspace: The workspace object

        Returns:
            String representation of workspace path
        """
        if workspace is None:
            return "none"
        if hasattr(workspace, 'workspace_path'):
            return workspace.workspace_path
        if hasattr(workspace, 'path'):
            return str(workspace.path)
        return str(id(workspace))

    def _find_workspace_dir(self) -> Optional[Path]:
        """
        Find the workspace root directory by traversing up the path hierarchy.

        Returns:
            Path to workspace directory if found, None otherwise
        """
        current_path = self.flow_storage_dir.resolve()
        for parent in current_path.parents:
            if parent.name == 'workspace':
                return parent
        return None

    def _get_ready_tasks(self, plan_instance: PlanInstance) -> List[PlanTask]:
        """
        Get tasks that are ready to run based on their dependencies.

        A task is ready if:
        1. Its status is CREATED
        2. All its dependencies (in the 'needs' list) are COMPLETED
        """
        ready_tasks = []

        for task in plan_instance.tasks:
            if task.status != TaskStatus.CREATED:
                continue

            # Check if all dependencies are completed
            all_deps_satisfied = True
            for dep_task_id in task.needs:
                dep_task = next((t for t in plan_instance.tasks if t.id == dep_task_id), None)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_deps_satisfied = False
                    break

            if all_deps_satisfied:
                ready_tasks.append(task)

        return ready_tasks

    def _update_task_status(self, plan_instance: PlanInstance, task_id: str,
                           new_status: TaskStatus, error_message: Optional[str] = None) -> bool:
        """
        Update the status of a specific task in a plan instance.
        """
        task = next((t for t in plan_instance.tasks if t.id == task_id), None)
        if not task:
            return False

        task.status = new_status
        if new_status == TaskStatus.RUNNING and task.started_at is None:
            task.started_at = datetime.now()
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.now()

        if error_message:
            task.error_message = error_message

        # Save the updated instance
        self._save_plan_instance(plan_instance)

        # Emit signal for task status update
        plan_signal_manager.task_status_updated.emit(
            plan_instance.project_name,
            plan_instance.plan_id,
            plan_instance.instance_id,
            task_id
        )

        return True

    def _update_plan_status(self, plan_instance: PlanInstance, new_status: PlanStatus) -> bool:
        """
        Update the status of a plan instance.
        """
        plan_instance.status = new_status
        if new_status == PlanStatus.RUNNING and plan_instance.started_at is None:
            plan_instance.started_at = datetime.now()
        elif new_status in [PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED]:
            plan_instance.completed_at = datetime.now()

        # Save the updated instance
        self._save_plan_instance(plan_instance)

        # Emit signal for plan instance status update
        plan_signal_manager.plan_instance_status_updated.emit(
            plan_instance.project_name,
            plan_instance.plan_id,
            plan_instance.instance_id
        )

        return True
    
    def _get_flow_dir(self, project_name: str, plan_id: str) -> Path:
        """Get the directory path for a specific plan.

        Args:
            project_name: Name of the project (used as identifier)
            plan_id: Unique ID of the plan
        """
        # Create directory structure as workspace/projects/项目名/plans
        workspace_path = self._find_workspace_dir()

        if workspace_path:
            # Use the proper workspace/projects/project_name/plans structure
            project_plans_dir = workspace_path / "projects" / project_name / "plans"
        else:
            # Fallback to the original approach if we can't find workspace
            project_plans_dir = self.flow_storage_dir.parent / "projects" / project_name / "plans"

        project_plans_dir.mkdir(parents=True, exist_ok=True)
        return project_plans_dir / plan_id

    def _save_plan(self, plan: Plan) -> None:
        """Save a Plan to disk atomically."""
        plan_dir = self._get_flow_dir(plan.project_name, plan.id)
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for serialization
        plan_data = asdict(plan)
        plan_data['created_at'] = plan_data['created_at'].isoformat()
        plan_data['status'] = plan_data['status'].value  # Convert enum to string
        plan_data['tasks'] = []

        for task in plan.tasks:
            task_dict = asdict(task)
            task_dict['created_at'] = task.created_at.isoformat()
            task_dict['started_at'] = task.started_at.isoformat() if task.started_at else None
            task_dict['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
            task_dict['status'] = task.status.value  # Convert enum to string
            plan_data['tasks'].append(task_dict)

        # Write to temporary file first
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            dir=plan_dir,
            suffix='.tmp'
        )

        try:
            yaml.dump(plan_data, temp_file, default_flow_style=False, allow_unicode=True)
            temp_file.close()

            # Atomically move the temporary file to the target location
            target_path = plan_dir / "plan.yml"
            shutil.move(temp_file.name, target_path)
        except Exception:
            # Clean up the temporary file if something went wrong
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise

    def _save_plan_instance(self, plan_instance: PlanInstance) -> None:
        """Save a PlanInstance to disk atomically."""
        plan_dir = self._get_flow_dir(plan_instance.project_name, plan_instance.plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for serialization
        instance_data = asdict(plan_instance)
        instance_data['created_at'] = instance_data['created_at'].isoformat()
        instance_data['started_at'] = instance_data['started_at'].isoformat() if instance_data['started_at'] else None
        instance_data['completed_at'] = instance_data['completed_at'].isoformat() if instance_data['completed_at'] else None
        instance_data['status'] = instance_data['status'].value  # Convert enum to string

        instance_data['tasks'] = []
        for task in plan_instance.tasks:
            task_dict = asdict(task)
            task_dict['created_at'] = task.created_at.isoformat()
            task_dict['started_at'] = task.started_at.isoformat() if task.started_at else None
            task_dict['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
            task_dict['status'] = task.status.value  # Convert enum to string
            instance_data['tasks'].append(task_dict)

        # Write to temporary file first
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            dir=plan_dir,
            suffix='.tmp'
        )

        try:
            yaml.dump(instance_data, temp_file, default_flow_style=False, allow_unicode=True)
            temp_file.close()

            # Atomically move the temporary file to the target location
            # Use the instance_id as the filename to support multiple instances
            target_path = plan_dir / f"plan_instance_{plan_instance.instance_id}.yml"
            shutil.move(temp_file.name, target_path)
        except Exception:
            # Clean up the temporary file if something went wrong
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise

    def start_plan_execution(self, plan_instance: PlanInstance) -> bool:
        """
        Start the execution of a plan instance.

        This sets the plan status to RUNNING and marks eligible tasks as READY.
        """
        if plan_instance.status != PlanStatus.CREATED:
            return False  # Can only start execution of a CREATED plan

        # Update plan status to RUNNING
        self._update_plan_status(plan_instance, PlanStatus.RUNNING)

        # Mark initial ready tasks (those with no dependencies)
        for task in plan_instance.tasks:
            if task.status == TaskStatus.CREATED and len(task.needs) == 0:
                self._update_task_status(plan_instance, task.id, TaskStatus.READY)

        return True

    def get_next_ready_tasks(self, plan_instance: PlanInstance) -> List[PlanTask]:
        """
        Get the next tasks that are ready to be executed based on dependencies.
        """
        return self._get_ready_tasks(plan_instance)

    def mark_task_running(self, plan_instance: PlanInstance, task_id: str) -> bool:
        """
        Mark a task as running.
        """
        return self._update_task_status(plan_instance, task_id, TaskStatus.RUNNING)

    def mark_task_completed(self, plan_instance: PlanInstance, task_id: str) -> bool:
        """
        Mark a task as completed and update dependent tasks to READY if their
        dependencies are satisfied.
        """
        success = self._update_task_status(plan_instance, task_id, TaskStatus.COMPLETED)
        if not success:
            return False

        # Check if there are any tasks that become ready due to this completion
        for task in plan_instance.tasks:
            if task.status == TaskStatus.CREATED:
                # Check if all dependencies are now satisfied
                all_deps_satisfied = True
                for dep_task_id in task.needs:
                    dep_task = next((t for t in plan_instance.tasks if t.id == dep_task_id), None)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_deps_satisfied = False
                        break

                if all_deps_satisfied:
                    self._update_task_status(plan_instance, task.id, TaskStatus.READY)

        # Check if the entire plan is completed
        incomplete_tasks = [t for t in plan_instance.tasks
                           if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]]

        if not incomplete_tasks:
            self._update_plan_status(plan_instance, PlanStatus.COMPLETED)

        return True

    def mark_task_failed(self, plan_instance: PlanInstance, task_id: str, error_message: str) -> bool:
        """
        Mark a task as failed.
        """
        success = self._update_task_status(plan_instance, task_id, TaskStatus.FAILED, error_message)
        if success:
            # Mark the entire plan as failed
            self._update_plan_status(plan_instance, PlanStatus.FAILED)
        return success

    def cancel_plan(self, plan_instance: PlanInstance) -> bool:
        """
        Cancel an entire plan instance.

        This marks the plan as CANCELLED and all non-completed tasks as CANCELLED too.
        """
        # Update all non-completed tasks to cancelled
        for task in plan_instance.tasks:
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
                self._update_task_status(plan_instance, task.id, TaskStatus.CANCELLED)

        # Update the plan status to cancelled
        return self._update_plan_status(plan_instance, PlanStatus.CANCELLED)

    def cancel_task(self, plan_instance: PlanInstance, task_id: str) -> bool:
        """
        Cancel a specific task in a plan instance.
        """
        return self._update_task_status(plan_instance, task_id, TaskStatus.CANCELLED)
    
    def create_plan(self, project_name: str, name: str, description: str,
                        tasks: List[PlanTask], metadata: Optional[Dict] = None) -> Plan:
        """Create a new Plan.

        Args:
            project_name: Name of the project (used as identifier)
            name: Name of the plan
            description: Description of the plan
            tasks: List of tasks in the plan
            metadata: Optional metadata for the plan
        """
        plan_id = f"p_{int(datetime.now().timestamp())}_{len(tasks)}"
        plan = Plan(
            id=plan_id,
            project_name=project_name,  # Using project name as the identifier
            name=name,
            description=description,
            tasks=tasks,
            metadata=metadata or {}
        )

        self._save_plan(plan)

        # Emit signal for plan creation
        plan_signal_manager.plan_created.emit(project_name, plan_id)

        return plan

    def create_plan_instance(self, plan: Plan) -> PlanInstance:
        """Create a new PlanInstance from a Plan."""
        import uuid
        instance_id = f"pi_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        # Copy tasks from the plan to the instance
        instance_tasks = []
        for task in plan.tasks:
            instance_task = PlanTask(
                id=task.id,
                name=task.name,
                description=task.description,
                title=task.title,
                parameters=task.parameters.copy(),
                needs=task.needs.copy(),
                status=TaskStatus.CREATED
            )
            instance_tasks.append(instance_task)

        plan_instance = PlanInstance(
            plan_id=plan.id,
            instance_id=instance_id,
            project_name=plan.project_name,  # This is actually the project name used as identifier
            tasks=instance_tasks,
            metadata=plan.metadata.copy()
        )

        self._save_plan_instance(plan_instance)

        # Emit signal for plan instance creation
        plan_signal_manager.plan_instance_created.emit(
            plan_instance.project_name,
            plan_instance.plan_id,
            plan_instance.instance_id
        )

        return plan_instance

    def sync_plan_instance(self, plan_instance: PlanInstance, plan: Plan) -> PlanInstance:
        """
        Sync a plan instance with the latest plan definition.

        This updates mutable fields for tasks that have not started yet and
        appends any new tasks introduced in the plan.
        """
        # Validate the plan tasks before syncing to ensure no invalid agent roles or dependencies
        validated_plan_tasks = self._validate_and_clean_tasks(plan.tasks)

        existing_tasks = {task.id: task for task in plan_instance.tasks}

        for plan_task in validated_plan_tasks:
            if plan_task.id in existing_tasks:
                instance_task = existing_tasks[plan_task.id]
                if instance_task.status in {TaskStatus.CREATED, TaskStatus.READY}:
                    instance_task.name = plan_task.name
                    instance_task.description = plan_task.description
                    instance_task.title = plan_task.title
                    instance_task.parameters = plan_task.parameters.copy()
                    instance_task.needs = plan_task.needs.copy()
                continue

            instance_task = PlanTask(
                id=plan_task.id,
                name=plan_task.name,
                description=plan_task.description,
                title=plan_task.title,
                parameters=plan_task.parameters.copy(),
                needs=plan_task.needs.copy(),
                status=TaskStatus.CREATED,
            )
            plan_instance.tasks.append(instance_task)

        self._save_plan_instance(plan_instance)
        return plan_instance

    def load_plan(self, project_name: str, plan_id: str) -> Optional[Plan]:
        """Load a Plan from disk.

        Args:
            project_name: Name of the project (used as identifier)
            plan_id: ID of the plan to load
        """
        plan_dir = self._get_flow_dir(project_name, plan_id)
        plan_path = plan_dir / "plan.yml"

        if not plan_path.exists():
            return None

        with open(plan_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert timestamps back to datetime objects
        created_at = datetime.fromisoformat(data['created_at'])

        # Reconstruct tasks
        tasks = []
        for task_data in data.get('tasks', []):
            task = PlanTask(
                id=task_data['id'],
                name=task_data['name'],
                description=task_data['description'],
                title=task_data.get('title', 'other'),  # Default to 'other' if title is missing
                parameters=task_data.get('parameters', {}),
                needs=task_data.get('needs', []),
                status=TaskStatus(task_data.get('status', 'created')),  # Convert string back to enum
                created_at=datetime.fromisoformat(task_data['created_at']),
                started_at=datetime.fromisoformat(task_data['started_at']) if task_data.get('started_at') else None,
                completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data.get('completed_at') else None,
                error_message=task_data.get('error_message')
            )
            tasks.append(task)

        plan = Plan(
            id=data['id'],
            project_name=data.get('project_name', project_name),
            name=data['name'],
            description=data['description'],
            tasks=tasks,
            created_at=created_at,
            status=PlanStatus(data.get('status', 'created')),  # Convert string back to enum
            metadata=data.get('metadata', {})
        )

        return plan

    def update_plan(
        self,
        project_name: str,
        plan_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tasks: Optional[List[PlanTask]] = None,
        append_tasks: Optional[List[PlanTask]] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[Plan]:
        """
        Update an existing Plan definition.

        Args:
            project_name: Name of the project (used as identifier)
            plan_id: ID of the plan to update
            name: New name for the plan (optional)
            description: New description for the plan (optional)
            tasks: New list of tasks for the plan (optional)
            append_tasks: Additional tasks to append to the plan (optional)
            metadata: Additional metadata to update (optional)
        """
        plan = self.load_plan(project_name, plan_id)
        if not plan:
            return None

        if name is not None:
            plan.name = name
        if description is not None:
            plan.description = description
        if metadata:
            plan.metadata.update(metadata)

        if tasks is not None:
            # Validate agent roles in tasks to ensure they don't use reserved names
            validated_tasks = self._validate_and_clean_tasks(tasks)
            plan.tasks = validated_tasks
        if append_tasks:
            # Validate agent roles in appended tasks to ensure they don't use reserved names
            validated_append_tasks = self._validate_and_clean_tasks(append_tasks)
            plan.tasks.extend(validated_append_tasks)

        self._save_plan(plan)

        # Emit signal for plan update
        plan_signal_manager.plan_updated.emit(project_name, plan_id)

        return plan

    def _validate_and_clean_tasks(self, tasks: Optional[List[PlanTask]]) -> List[PlanTask]:
        """
        Validate and clean tasks to ensure they don't have invalid agent roles or unmet dependencies.

        Args:
            tasks: List of tasks to validate

        Returns:
            List of validated and cleaned tasks
        """
        if not tasks:
            return []

        # Reserved agent roles that should not be used in plans
        reserved_roles = {'system', 'user', 'assistant', 'none', ''}

        # Create a set of valid task IDs for dependency checking
        valid_task_ids = {task.id for task in tasks}

        validated_tasks = []
        for task in tasks:
            # Check if title is a reserved role
            if task.title.lower() in reserved_roles:
                # Skip tasks with invalid agent roles
                continue

            # Check if all dependencies exist in the task list
            invalid_dependencies = [dep for dep in task.needs if dep not in valid_task_ids]
            if invalid_dependencies:
                # Skip tasks with invalid dependencies
                continue

            # Check for circular dependencies by validating the dependency chain
            if self._has_circular_dependency(task, tasks):
                # Skip tasks that would create circular dependencies
                continue

            validated_tasks.append(task)

        return validated_tasks

    def _has_circular_dependency(self, task: PlanTask, all_tasks: List[PlanTask]) -> bool:
        """
        Check if adding this task would create a circular dependency.

        Args:
            task: The task to check
            all_tasks: All tasks in the plan

        Returns:
            True if circular dependency exists, False otherwise
        """
        # Create a map of task ID to dependencies for quick lookup
        deps_map = {t.id: set(t.needs) for t in all_tasks}

        # Check if this task creates a circular dependency
        visited = set()
        queue = [task.id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            # Get dependencies of current task
            current_deps = deps_map.get(current_id, set())

            for dep_id in current_deps:
                # If we reach back to the original task, there's a cycle
                if dep_id == task.id:
                    return True
                if dep_id not in visited:
                    queue.append(dep_id)

        return False

    def load_plan_instance(self, project_name: str, plan_id: str, instance_id: str) -> Optional[PlanInstance]:
        """Load a PlanInstance from disk.

        Args:
            project_name: Name of the project (used as identifier)
            plan_id: ID of the plan
            instance_id: ID of the plan instance
        """
        plan_dir = self._get_flow_dir(project_name, plan_id)
        plan_instance_path = plan_dir / f"plan_instance_{instance_id}.yml"

        if not plan_instance_path.exists():
            return None

        with open(plan_instance_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert timestamps back to datetime objects
        created_at = datetime.fromisoformat(data['created_at'])
        started_at = datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        completed_at = datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None

        # Reconstruct tasks
        tasks = []
        for task_data in data.get('tasks', []):
            task = PlanTask(
                id=task_data['id'],
                name=task_data['name'],
                description=task_data['description'],
                title=task_data.get('title', 'other'),  # Default to 'other' if title is missing
                parameters=task_data.get('parameters', {}),
                needs=task_data.get('needs', []),
                status=TaskStatus(task_data.get('status', 'created')),  # Convert string back to enum
                created_at=datetime.fromisoformat(task_data['created_at']),
                started_at=datetime.fromisoformat(task_data['started_at']) if task_data.get('started_at') else None,
                completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data.get('completed_at') else None,
                error_message=task_data.get('error_message')
            )
            tasks.append(task)

        plan_instance = PlanInstance(
            plan_id=data['plan_id'],
            instance_id=data['instance_id'],
            project_name=data.get('project_name', project_name),
            tasks=tasks,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            status=PlanStatus(data.get('status', 'created')),  # Convert string back to enum
            metadata=data.get('metadata', {})
        )

        return plan_instance
    
    def get_all_plans_for_project(self, project_name: str) -> List[Plan]:
        """Get all Plans for a specific project.

        Args:
            project_name: Name of the project (used as identifier)
        """
        # Use the project-specific plans directory
        workspace_path = self._find_workspace_dir()

        if workspace_path:
            project_plans_dir = workspace_path / "projects" / project_name / "plans"
        else:
            # Fallback to the original approach if we can't find workspace
            project_plans_dir = self.flow_storage_dir.parent / "projects" / project_name / "plans"

        if not project_plans_dir.exists():
            return []

        # Get all plan directories in the project's plans folder
        plan_dirs = [d for d in project_plans_dir.iterdir() if d.is_dir()]

        plans = []
        for plan_dir in plan_dirs:
            plan_id = plan_dir.name  # Plan ID is now the directory name
            plan = self.load_plan(project_name, plan_id)
            if plan:
                plans.append(plan)

        return plans

    def get_all_instances_for_plan(self, project_name: str, plan_id: str) -> List[PlanInstance]:
        """Get all PlanInstances for a specific plan.

        Args:
            project_name: Name of the project (used as identifier)
            plan_id: ID of the plan
        """
        plan_dir = self._get_flow_dir(project_name, plan_id)

        instances = []
        if plan_dir.exists():
            # Look for all plan instance files in the plan directory
            for file_path in plan_dir.glob("plan_instance_*.yml"):
                # Extract instance_id from filename
                filename = file_path.name
                # Format: plan_instance_{instance_id}.yml
                if filename.startswith("plan_instance_") and filename.endswith(".yml"):
                    instance_id = filename[len("plan_instance_"):-len(".yml")]

                    # Load the instance
                    instance = self.load_plan_instance(project_name, plan_id, instance_id)
                    if instance:
                        instances.append(instance)

        return instances

    def get_last_active_plan_for_project(self, project_name: str) -> Optional[Plan]:
        """
        Get the most recent plan for a project that is in an active state.
        Returns the plan if it's active (CREATED or RUNNING), otherwise returns None.

        Args:
            project_name: Name of the project (used as identifier)

        Returns:
            Plan if the most recent plan is active, otherwise None
        """
        plans = self.get_all_plans_for_project(project_name)
        if not plans:
            return None

        # Sort plans by creation date, most recent first
        sorted_plans = sorted(plans, key=lambda p: p.created_at, reverse=True)

        # Return the first plan that is in an active state (CREATED or RUNNING)
        for plan in sorted_plans:
            if plan.status in [PlanStatus.CREATED, PlanStatus.RUNNING]:
                return plan

        # If no active plan is found, return None
        return None