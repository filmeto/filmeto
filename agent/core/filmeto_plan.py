"""
Filmeto Agent Plan Manager Module

Handles plan operations, task execution, and plan-related event emission.
"""
import logging
import uuid
from typing import AsyncGenerator, List, Optional, Any, TYPE_CHECKING

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import TextContent, PlanContent, PlanTaskContent
from agent.core.filmeto_utils import truncate_text
from agent.plan.plan_models import TaskStatus

if TYPE_CHECKING:
    from agent.crew.crew_member import CrewMember
    from agent.plan.plan_models import Plan, PlanInstance, PlanTask
    from agent.plan.plan_service import PlanService
    from agent.event.agent_event import AgentEvent
    from agent.chat.agent_chat_signals import AgentChatSignals
    from agent.core.filmeto_routing import FilmetoRoutingManager

logger = logging.getLogger(__name__)


class FilmetoPlanManager:
    """
    Manages plan operations and task execution for FilmetoAgent.
    """

    def __init__(
        self,
        plan_service: "PlanService",
        signals: "AgentChatSignals",
        routing_manager: "FilmetoRoutingManager",
        resolve_project_name: callable,
    ):
        """Initialize the plan manager."""
        self._plan_service = plan_service
        self._signals = signals
        self._routing_manager = routing_manager
        self._resolve_project_name = resolve_project_name

    def create_plan(self, project_name: str, user_message: str, source: str = "producer") -> Optional["Plan"]:
        """Create a new plan for the project."""
        if not project_name:
            return None

        name = "Producer Plan"
        description = truncate_text(user_message)
        metadata = {"source": source, "request": user_message}

        return self._plan_service.create_plan(
            project_name=project_name,
            name=name,
            description=description,
            tasks=[],
            metadata=metadata,
        )

    def get_active_plan(self, project_name: str) -> Optional["Plan"]:
        """Get the last active plan for a project."""
        if not project_name:
            return None
        return self._plan_service.get_last_active_plan_for_project(project_name)

    async def emit_plan_update(
        self,
        plan: "Plan",
        session_id: str,
        sender_id: str,
        sender_name: str,
        message_id: str,
        operation: str = "update",
    ) -> None:
        """Emit a plan update event with PlanContent."""
        plan_content = PlanContent.from_plan(plan, operation=operation)

        meta = {
            "event_type": "plan_updated",
            "session_id": session_id,
            "plan_id": plan.id,
        }

        msg = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            metadata=meta,
            message_id=message_id,
            structured_content=[plan_content],
        )
        logger.info(f"Sending plan update: id={plan.id}, operation={operation}")
        await self._signals.send_agent_message(msg)

    async def emit_plan_task_update(
        self,
        task: "PlanTask",
        plan_id: str,
        session_id: str,
        sender_id: str,
        sender_name: str,
        message_id: str,
        previous_status: Optional[str] = None,
    ) -> None:
        """Emit a plan task update event with PlanTaskContent."""
        plan_task_content = PlanTaskContent.from_task(
            task=task,
            plan_id=plan_id,
            previous_status=previous_status
        )

        meta = {
            "event_type": "plan_task_updated",
            "session_id": session_id,
            "plan_id": plan_id,
            "task_id": task.id,
        }

        msg = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            metadata=meta,
            message_id=message_id,
            structured_content=[plan_task_content],
        )
        logger.info(f"Sending plan task update: plan_id={plan_id}, task_id={task.id}, status={task.status.value}")
        await self._signals.send_agent_message(msg)

    def build_producer_message(self, user_message: str, plan_id: str, retry: bool = False) -> str:
        """Build a message for the producer agent."""
        return "\n".join([
            f"User message: {user_message}",
            f"Current plan id: {plan_id}",
            "Please process this message appropriately using your skills and judgment.",
            "If a plan needs to be created or updated, use the appropriate planning skills.",
            "If other crew members should handle this, delegate appropriately.",
            "Provide a helpful response to the user."
        ])

    def build_task_message(self, task: "PlanTask", plan_id: str) -> str:
        """Build a message for a task assignment."""
        import json
        parameters = json.dumps(task.parameters or {}, ensure_ascii=True)
        needs = ", ".join(task.needs) if task.needs else "none"
        return "\n".join([
            f"@{task.title}",
            f"Plan id: {plan_id}",
            f"Task id: {task.id}",
            f"Task name: {task.name}",
            f"Task description: {task.description}",
            f"Dependencies: {needs}",
            f"Parameters: {parameters}",
            "Respond with your output. If needed, update the plan with plan_update.",
        ])

    def build_task_intro_text(self, task: "PlanTask", plan: "Plan") -> str:
        """Build introductory text for a task."""
        parts = [
            f"**Task:** {task.name}",
            "",
            f"{task.description}",
        ]

        if task.needs:
            deps_text = ", ".join(task.needs)
            parts.append("")
            parts.append(f"**Depends on:** {deps_text}")

        if task.parameters:
            parts.append("")
            parts.append("**Parameters:**")
            for key, value in task.parameters.items():
                parts.append(f"- {key}: {value}")

        return "\n".join(parts)

    def check_response_error(self, response: Optional[str]) -> bool:
        """Check if a response contains error indicators."""
        if not response:
            return False
        lowered = response.lower()
        return "llm service is not configured" in lowered or "error calling llm" in lowered

    def dependencies_satisfied(self, plan_instance: "PlanInstance", task: "PlanTask") -> bool:
        """Check if all dependencies for a task are satisfied."""
        if not task.needs:
            return True
        for dependency_id in task.needs:
            dependency = next((t for t in plan_instance.tasks if t.id == dependency_id), None)
            if not dependency or dependency.status != TaskStatus.COMPLETED:
                return False
        return True

    def get_ready_tasks(self, plan_instance: "PlanInstance") -> List["PlanTask"]:
        """Get all tasks that are ready to execute."""
        ready = []
        for task in plan_instance.tasks:
            if task.status not in {TaskStatus.CREATED, TaskStatus.READY}:
                continue
            if self.dependencies_satisfied(plan_instance, task):
                ready.append(task)
        return ready

    def has_incomplete_tasks(self, plan_instance: "PlanInstance") -> bool:
        """Check if there are any incomplete tasks."""
        for task in plan_instance.tasks:
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED}:
                return True
        return False

    async def handle_producer_flow(
        self,
        initial_prompt: AgentMessage,
        producer_agent: "CrewMember",
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        """Handle the producer agent flow."""
        from agent.core.filmeto_utils import extract_text_content

        try:
            project_name = self._resolve_project_name()

            # Determine the active plan ID
            active_plan = self.get_active_plan(project_name) if project_name else None
            active_plan_id = active_plan.id if active_plan else None

            # Generate message_id for producer's messages
            producer_message_id = str(uuid.uuid4())

            # Stream to the producer agent
            async for event in self._routing_manager.stream_crew_member(
                producer_agent,
                extract_text_content(initial_prompt),
                plan_id=active_plan_id,
                session_id=session_id,
                message_id=producer_message_id,
            ):
                try:
                    yield event
                except Exception as e:
                    logger.error("Exception in handle_producer_flow while yielding event", exc_info=True)

            # Check if a plan was created during the interaction
            if project_name:
                latest_plan = self.get_active_plan(project_name)
                if latest_plan and latest_plan.id != active_plan_id:
                    active_plan_id = latest_plan.id

                    # Emit plan update
                    await self.emit_plan_update(
                        plan=latest_plan,
                        session_id=session_id,
                        sender_id=producer_agent.config.name,
                        sender_name=producer_agent.config.name,
                        message_id=producer_message_id,
                        operation="create",
                    )

                    # Execute plan tasks if any
                    if latest_plan and latest_plan.tasks:
                        async for event in self.execute_plan_tasks(
                            plan=latest_plan,
                            session_id=session_id,
                        ):
                            try:
                                yield event
                            except Exception as e:
                                logger.error("Exception in handle_producer_flow while yielding plan task event", exc_info=True)

        except Exception as e:
            logger.error("Exception in handle_producer_flow", exc_info=True)

    async def execute_plan_tasks(
        self,
        plan: "Plan",
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        """Execute all ready tasks in a plan."""
        try:
            plan_instance = self._plan_service.create_plan_instance(plan)
            self._plan_service.start_plan_execution(plan_instance)

            while True:
                ready_tasks = self.get_ready_tasks(plan_instance)
                if not ready_tasks:
                    if self.has_incomplete_tasks(plan_instance):
                        async for event in self._stream_error(
                            "Plan execution blocked by unmet dependencies or missing agents.",
                            session_id,
                        ):
                            try:
                                yield event
                            except Exception as e:
                                logger.error("Exception in execute_plan_tasks while yielding blocked event", exc_info=True)
                    break

                for task in ready_tasks:
                    async for event in self._execute_single_task(
                        task, plan, plan_instance, session_id
                    ):
                        yield event

                # Reload plan to check for updates
                updated_plan = self._plan_service.load_plan(plan.project_name, plan.id)
                if updated_plan:
                    plan_instance = self._plan_service.sync_plan_instance(plan_instance, updated_plan)

        except Exception as e:
            logger.error("Exception in execute_plan_tasks", exc_info=True)

    async def _execute_single_task(
        self,
        task: "PlanTask",
        plan: "Plan",
        plan_instance: "PlanInstance",
        session_id: str,
    ) -> AsyncGenerator["AgentEvent", None]:
        """Execute a single plan task."""
        from agent.core.filmeto_crew import FilmetoCrewManager

        previous_status = task.status.value
        self._plan_service.mark_task_running(plan_instance, task.id)

        # Get updated task
        updated_task = next((t for t in plan_instance.tasks if t.id == task.id), None)

        # Find target agent - need to look up from crew manager through routing manager
        # This is a bit of a hack, we should refactor to pass crew manager directly
        target_agent = None
        for member in self._routing_manager._crew_manager.crew_members.values():
            if member.config.name.lower() == task.title.lower():
                target_agent = member
                break

        if not target_agent:
            error_message = f"Crew member '{task.title}' not found for task {task.id}."
            self._plan_service.mark_task_failed(plan_instance, task.id, error_message)

            # Get updated task after failure
            failed_task = next((t for t in plan_instance.tasks if t.id == task.id), None)
            if failed_task:
                await self.emit_plan_task_update(
                    task=failed_task,
                    plan_id=plan.id,
                    session_id=session_id,
                    sender_id="system",
                    sender_name="System",
                    message_id=str(uuid.uuid4()),
                    previous_status=previous_status,
                )

            async for event in self._stream_error(error_message, session_id):
                try:
                    yield event
                except Exception as e:
                    logger.error("Exception in execute_plan_tasks while yielding error event", exc_info=True)
            return

        # Generate message_id for this task
        task_message_id = str(uuid.uuid4())

        # Emit plan task update for running status
        if updated_task:
            await self.emit_plan_task_update(
                task=updated_task,
                plan_id=plan.id,
                session_id=session_id,
                sender_id=target_agent.config.name,
                sender_name=target_agent.config.name,
                message_id=task_message_id,
                previous_status=previous_status,
            )

        # Emit task intro
        task_intro_text = self.build_task_intro_text(task, plan)
        task_intro_msg = AgentMessage(
            sender_id=target_agent.config.name,
            sender_name=target_agent.config.name.capitalize(),
            message_id=task_message_id,
            structured_content=[TextContent(
                text=task_intro_text,
                title=task.name,
                description=f"Task from plan: {plan.name}"
            )]
        )
        logger.info(f"Sending task intro: id={task_intro_msg.message_id}, sender='{target_agent.config.name}', task_id={task.id}")
        await self._signals.send_agent_message(task_intro_msg)

        # Execute task
        task_message = self.build_task_message(task, plan.id)
        async for event in self._routing_manager.stream_crew_member(
            target_agent,
            task_message,
            plan_id=plan.id,
            session_id=session_id,
            metadata={"plan_id": plan.id, "task_id": task.id},
            message_id=task_message_id,
        ):
            try:
                yield event
            except Exception as e:
                logger.error("Exception in execute_plan_tasks while yielding task event", exc_info=True)

        # Mark task completed
        previous_status = updated_task.status.value if updated_task else TaskStatus.RUNNING.value
        self._plan_service.mark_task_completed(plan_instance, task.id)

        # Get updated task and emit completion
        completed_task = next((t for t in plan_instance.tasks if t.id == task.id), None)
        if completed_task:
            await self.emit_plan_task_update(
                task=completed_task,
                plan_id=plan.id,
                session_id=session_id,
                sender_id=target_agent.config.name,
                sender_name=target_agent.config.name,
                message_id=task_message_id,
                previous_status=previous_status,
            )

    async def _stream_error(
        self, message: str, session_id: str
    ) -> AsyncGenerator["AgentEvent", None]:
        """Stream an error message event."""
        from agent.react import AgentEvent, AgentEventType
        from agent.core.filmeto_utils import extract_text_content

        error_msg = AgentMessage(
            sender_id="system",
            sender_name="System",
            structured_content=[TextContent(text=message)]
        )
        logger.info(f"Sending error message: id={error_msg.message_id}, sender='system'")
        error_msg.metadata["session_id"] = session_id
        await self._signals.send_agent_message(error_msg)

        yield AgentEvent.error(
            error_message=message,
            project_name=self._resolve_project_name() or "default",
            react_type="system",
            run_id="",
            sender_id="system",
            sender_name="System",
        )
