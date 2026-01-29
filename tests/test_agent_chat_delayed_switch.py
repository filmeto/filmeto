"""
Test AgentChatWidget delayed project switching functionality.

This test verifies that agent instance switching is delayed until
the agent is actually needed, ensuring we use the workspace's
real current project rather than a stale reference.
"""
import sys
sys.path.insert(0, '.')

from agent.filmeto_agent import FilmetoAgent


class MockWorkspace:
    """Mock workspace for testing."""
    def __init__(self, path: str):
        self.workspace_path = path
        self._current_project = None

    def get_settings(self):
        return {'ai_services.default_model': 'gpt-4o-mini'}

    def get_project(self):
        return self._current_project

    def set_project(self, project):
        """Set the current project (simulates workspace project switch)."""
        self._current_project = project


class MockProject:
    """Mock project for testing."""
    def __init__(self, name: str):
        self.project_name = name


def test_delayed_switching():
    """Test that agent switching is delayed and uses workspace's real project."""
    print("\n" + "=" * 60)
    print("Testing Delayed Project Switching")
    print("=" * 60)

    FilmetoAgent.clear_all_instances()

    # Create mock workspace with initial project
    workspace = MockWorkspace("/tmp/test_delayed_ws")
    workspace.set_project(MockProject("project_a"))

    # Simulate AgentChatWidget behavior
    class DelayedAgentWidget:
        def __init__(self, workspace):
            self.workspace = workspace
            self._current_project_name = None
            self._target_project_name = None
            self._agent_needs_sync = False
            self.agent = None

        def on_project_switch(self, project):
            """Handle project switch request (delayed)."""
            new_project_name = None
            if project:
                if hasattr(project, 'project_name'):
                    new_project_name = project.project_name
                elif isinstance(project, str):
                    new_project_name = project

            if not new_project_name:
                new_project_name = "default"

            print(f"   on_project_switch called: target={new_project_name} (delayed)")
            self._target_project_name = new_project_name
            self._agent_needs_sync = True

        def sync_agent_instance(self):
            """Sync agent instance with workspace's real current project."""
            if not self._agent_needs_sync:
                return

            # Get REAL current project from workspace
            current_workspace_project = self.workspace.get_project()

            real_project_name = None
            if current_workspace_project:
                if hasattr(current_workspace_project, 'project_name'):
                    real_project_name = current_workspace_project.project_name

            if not real_project_name:
                real_project_name = self._target_project_name or "default"

            print(f"   sync_agent_instance: syncing to real project='{real_project_name}'")

            self.agent = FilmetoAgent.get_instance(
                workspace=self.workspace,
                project_name=real_project_name,
                model="gpt-4o-mini"
            )

            self._current_project_name = real_project_name
            self._agent_needs_sync = False

        def get_current_project_name(self):
            return self._current_project_name

        def get_target_project_name(self):
            if self._agent_needs_sync and self._target_project_name:
                return self._target_project_name
            return self._current_project_name

        def get_workspace_current_project_name(self):
            project = self.workspace.get_project()
            if project and hasattr(project, 'project_name'):
                return project.project_name
            return None

    widget = DelayedAgentWidget(workspace)

    print("\n1. Initial state:")
    print(f"   Widget current project: {widget.get_current_project_name()}")
    print(f"   Widget target project: {widget.get_target_project_name()}")
    print(f"   Workspace current project: {widget.get_workspace_current_project_name()}")

    print("\n2. Requesting switch to project_b (but workspace still on project_a)...")
    widget.on_project_switch("project_b")

    print(f"   Widget current project: {widget.get_current_project_name()}")
    print(f"   Widget target project: {widget.get_target_project_name()}")
    print(f"   Workspace current project: {widget.get_workspace_current_project_name()}")
    print(f"   Agent instance: {widget.agent}")
    print("   → Agent NOT switched yet (delayed)")

    print("\n3. Now workspace actually switches to project_b...")
    workspace.set_project(MockProject("project_b"))

    print(f"   Workspace current project: {widget.get_workspace_current_project_name()}")
    print(f"   Widget still shows: current={widget.get_current_project_name()}, target={widget.get_target_project_name()}")

    print("\n4. Triggering agent sync (e.g., before sending message)...")
    widget.sync_agent_instance()

    print(f"   Widget current project: {widget.get_current_project_name()}")
    print(f"   Widget target project: {widget.get_target_project_name()}")
    print(f"   Agent instance: {widget.agent}")
    print("   → Agent switched to match workspace's REAL current project")
    print(f"   Active instances: {FilmetoAgent.list_instances()}")

    # Verify the agent is for project_b
    assert widget.get_current_project_name() == "project_b"
    assert widget.agent is not None

    print("\n5. Testing scenario: Request switch but workspace switches to different project...")

    # Request switch to project_c
    widget.on_project_switch("project_c")
    print(f"   Requested switch to: project_c")
    print(f"   Target project: {widget.get_target_project_name()}")

    # But workspace actually switches to project_d (not project_c)
    workspace.set_project(MockProject("project_d"))
    print(f"   Workspace actually switched to: {widget.get_workspace_current_project_name()}")

    # Sync should use workspace's real project (project_d), not target (project_c)
    widget.sync_agent_instance()

    print(f"   After sync - current project: {widget.get_current_project_name()}")
    assert widget.get_current_project_name() == "project_d", "Should sync to workspace's real project!"
    print("   ✓ Correctly synced to workspace's real project (project_d), not target (project_c)")

    print(f"   Active instances: {FilmetoAgent.list_instances()}")
    # Should have instances for project_b and project_d, not project_c
    assert f"/tmp/test_delayed_ws:project_b" in FilmetoAgent.list_instances()
    assert f"/tmp/test_delayed_ws:project_d" in FilmetoAgent.list_instances()
    assert f"/tmp/test_delayed_ws:project_c" not in FilmetoAgent.list_instances()
    print("   ✓ project_c instance was never created (used workspace's real project)")

    # Cleanup
    FilmetoAgent.clear_all_instances()

    print("\n" + "=" * 60)
    print("All delayed switching tests passed! ✓")
    print("=" * 60)


def test_stale_reference_prevention():
    """Test that delayed switching prevents using stale workspace project references."""
    print("\n" + "=" * 60)
    print("Testing Stale Reference Prevention")
    print("=" * 60)

    FilmetoAgent.clear_all_instances()

    workspace = MockWorkspace("/tmp/test_stale_ws")
    workspace.set_project(MockProject("project_x"))

    class SimpleWidget:
        def __init__(self, workspace):
            self.workspace = workspace
            self._current_project_name = None
            self._target_project_name = None
            self._agent_needs_sync = False
            self.agent = None

        def on_project_switch(self, project):
            if isinstance(project, str):
                self._target_project_name = project
            elif hasattr(project, 'project_name'):
                self._target_project_name = project.project_name
            self._agent_needs_sync = True

        def sync_agent_instance(self):
            if not self._agent_needs_sync:
                return

            # KEY: Get REAL project from workspace, not from target
            current_workspace_project = self.workspace.get_project()
            real_project_name = None
            if current_workspace_project:
                real_project_name = current_workspace_project.project_name

            if not real_project_name:
                real_project_name = self._target_project_name or "default"

            self.agent = FilmetoAgent.get_instance(
                workspace=self.workspace,
                project_name=real_project_name,
                model="gpt-4o-mini"
            )
            self._current_project_name = real_project_name
            self._agent_needs_sync = False

    widget = SimpleWidget(workspace)

    print("\n1. Widget requests switch to project_y")
    widget.on_project_switch("project_y")
    target = widget._target_project_name
    print(f"   Target set to: {target}")

    print("\n2. But before sync, workspace switches to project_z instead")
    workspace.set_project(MockProject("project_z"))
    print(f"   Workspace now: {workspace.get_project().project_name}")

    print("\n3. Widget syncs agent...")
    widget.sync_agent_instance()

    print(f"   Agent created for: {widget._current_project_name}")
    assert widget._current_project_name == "project_z", "Should use workspace's real project!"
    print("   ✓ Used workspace's real project (project_z), not stale target (project_y)")

    instances = FilmetoAgent.list_instances()
    print(f"   Active instances: {instances}")
    assert f"/tmp/test_stale_ws:project_z" in instances
    assert f"/tmp/test_stale_ws:project_y" not in instances
    print("   ✓ No instance created for stale target project_y")

    # Cleanup
    FilmetoAgent.clear_all_instances()

    print("\n" + "=" * 60)
    print("Stale reference prevention test passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_delayed_switching()
    test_stale_reference_prevention()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓✓✓")
    print("=" * 60)
    print("\nSummary:")
    print("- Project switching is delayed until agent is needed")
    print("- Agent sync uses workspace's REAL current project")
    print("- Prevents stale references when workspace changes")
    print("- Ensures agent instance matches actual workspace state")
