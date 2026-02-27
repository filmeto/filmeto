"""Agent chat plan widget for showing active execution plan.

This module provides a QML-based plan widget that replaces the legacy Python
implementation, offering better performance and consistency with other QML components.
"""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QUrl, Slot, Signal, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

from app.ui.base_widget import BaseWidget
from app.ui.chat.plan.plan_bridge import PlanBridge

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.workspace import Workspace
    from agent import AgentMessage


class AgentChatPlanWidget(BaseWidget):
    """QML-based plan widget embedded in agent chat.

    This widget displays the active execution plan with real-time updates,
    including task status, crew member assignments, and progress tracking.

    Features:
    - Real-time plan updates via PlanBridge
    - Collapsible header with status counts (Running/Waiting/Success/Failed)
    - Task list with crew member info
    - Hardware-accelerated QML rendering
    - Transparent background for theme compatibility

    Signals:
        planSelected: Emitted when a plan is selected (plan_id)
        expandedChanged: Emitted when expanded state changes (is_expanded)
    """

    planSelected = Signal(str)
    expandedChanged = Signal(bool)

    # Height constants for splitter integration
    header_height = 40
    _collapsed_height = 52
    _expanded_height = 260

    def __init__(self, workspace: "Workspace", parent=None):
        """Initialize the plan widget.

        Args:
            workspace: Workspace instance
            parent: Parent widget
        """
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        # Track expanded state
        self._is_expanded = False

        # Create bridge for data binding
        self._bridge = PlanBridge(workspace, self)

        # Create QML widget with transparent background
        self._quick_widget = QQuickWidget(self)
        self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

        # Enable transparent background for dark theme compatibility
        self._quick_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick_widget.setClearColor(Qt.transparent)

        # Expose bridge to QML
        self._quick_widget.rootContext().setContextProperty("_planBridge", self._bridge)

        # Load QML
        qml_path = Path(__file__).parent.parent.parent / "qml" / "chat" / "widgets" / "PlanWidget.qml"
        if not qml_path.exists():
            logger.error(f"QML file not found at: {qml_path}")
            return

        self._quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))

        # Check for errors
        if self._quick_widget.status() == QQuickWidget.Error:
            errors = self._quick_widget.errors()
            for error in errors:
                logger.error(f"QML Error: {error.toString()}")
            return

        # Get QML root and configure for panel mode
        self._qml_root = self._quick_widget.rootObject()
        if self._qml_root:
            self._qml_root.setProperty("mode", "panel")
            self._qml_root.setProperty("planBridge", self._bridge)

            # Connect to QML isExpanded changes
            self._qml_root.isExpandedChanged.connect(self._on_qml_expanded_changed)

        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._quick_widget)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Set fixed height initially
        self.setFixedHeight(self._collapsed_height)

        # Initial data load
        self._bridge.refresh_plan()

    def _on_qml_expanded_changed(self):
        """Handle QML isExpanded property change."""
        if not self._qml_root:
            return

        new_expanded = self._qml_root.property("isExpanded")
        if new_expanded != self._is_expanded:
            self._is_expanded = new_expanded
            self._update_height()
            self.expandedChanged.emit(self._is_expanded)

    def _update_height(self):
        """Update widget height based on expanded state."""
        target_height = self._expanded_height if self._is_expanded else self._collapsed_height

        # Animate height change
        self._height_animation = QPropertyAnimation(self, b"maximumHeight")
        self._height_animation.setDuration(200)
        self._height_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._height_animation.setStartValue(self.height())
        self._height_animation.setEndValue(target_height)
        self._height_animation.start()

        self.setFixedHeight(target_height)

    @property
    def is_expanded(self) -> bool:
        """Get current expanded state."""
        return self._is_expanded

    def on_project_switched(self, project_name: str):
        """Handle project switch.

        Args:
            project_name: New project name
        """
        self._bridge.on_project_switched()

    def refresh_plan(self):
        """Refresh plan data from service."""
        self._bridge.refresh_plan()

    def set_preferred_plan(self, plan_id: str):
        """Set the preferred plan ID to display.

        Args:
            plan_id: Plan ID to display
        """
        self._bridge.set_preferred_plan(plan_id)

    def has_tasks(self) -> bool:
        """Check if there are tasks to display.

        Returns:
            True if there are tasks, False otherwise
        """
        return self._bridge.hasTasks

    def toggle_expanded(self):
        """Toggle the expanded state of the plan details."""
        if self._qml_root:
            current = self._qml_root.property("isExpanded")
            self._qml_root.setProperty("isExpanded", not current)

    async def handle_agent_message(self, message: "AgentMessage"):
        """Handle an AgentMessage directly.

        Args:
            message: AgentMessage to handle
        """
        if not message:
            return

        # Check if this message contains plan update information
        if message.metadata:
            event_type = message.metadata.get("event_type", "")
            if event_type in ("plan_created", "plan_updated", "plan_update"):
                plan_id = message.metadata.get("plan_id")
                if plan_id:
                    self._bridge.set_preferred_plan(plan_id)
                self._bridge.refresh_plan()

        # Check structured_content for plan-related types
        if message.structured_content:
            from agent.chat.agent_chat_types import ContentType
            for content in message.structured_content:
                if hasattr(content, 'content_type'):
                    content_type_str = str(content.content_type).lower()
                    if content_type_str == "plan" or "plan" in content_type_str:
                        self._bridge.refresh_plan()
                        break

    def handle_stream_event(self, event, _session=None):
        """Handle stream event.

        Args:
            event: Stream event to handle
            _session: Session (unused)
        """
        if not event:
            return
        if event.event_type in ("plan_created", "plan_updated", "plan_update"):
            plan_id = event.data.get("plan_id") if event.data else None
            if plan_id:
                self._bridge.set_preferred_plan(plan_id)
            self._bridge.refresh_plan()

    @property
    def bridge(self) -> PlanBridge:
        """Get the plan bridge.

        Returns:
            PlanBridge instance
        """
        return self._bridge
