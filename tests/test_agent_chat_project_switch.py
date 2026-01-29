"""
Test AgentChatWidget project switching functionality.
"""
import asyncio
from agent.filmeto_agent import FilmetoAgent


class MockWorkspace:
    """Mock workspace for testing."""
    def __init__(self, path: str):
        self.workspace_path = path

    def get_settings(self):
        return {'ai_services.default_model': 'gpt-4o-mini'}

    def get_project(self):
        return None


class MockProject:
    """Mock project for testing."""
    def __init__(self, name: str):
        self.project_name = name


async def test_project_switching():
    """Test that project switching properly manages agent instances."""
    print("\n" + "=" * 60)
    print("Testing AgentChatWidget Project Switching")
    print("=" * 60)

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    # Create mock workspace
    workspace = MockWorkspace("/tmp/filmeto_test_workspace")

    # Simulate AgentChatWidget behavior
    class MockAgentChatWidget:
        def __init__(self, workspace):
            from agent.filmeto_agent import FilmetoAgent

            self.workspace = workspace
            self._current_project_name = None
            self._current_project = None
            self.agent = None

        def on_project_switch(self, project):
            """Handle project switching (simplified version)."""
            from agent.filmeto_agent import FilmetoAgent

            # Extract project name
            new_project_name = None
            if project:
                if hasattr(project, 'project_name'):
                    new_project_name = project.project_name
                elif hasattr(project, 'name'):
                    new_project_name = project.name
                elif isinstance(project, str):
                    new_project_name = project

            if not new_project_name:
                new_project_name = "default"

            # Check if this is actually a different project
            if self._current_project_name == new_project_name:
                print(f"   Already on project '{new_project_name}', no switch needed")
                return

            print(f"   Switching from '{self._current_project_name}' to '{new_project_name}'")

            # Update tracking
            self._current_project_name = new_project_name
            self._current_project = project

            # Get or create agent instance
            settings = self.workspace.get_settings()
            model = settings.get('ai_services.default_model', 'gpt-4o-mini')

            self.agent = FilmetoAgent.get_instance(
                workspace=self.workspace,
                project_name=new_project_name,
                model=model,
                temperature=0.7,
                streaming=True
            )

            print(f"   ✓ Agent instance: {FilmetoAgent._get_workspace_path(workspace)}:{new_project_name}")

        def get_current_project_name(self):
            return self._current_project_name

        def get_agent_instance_key(self):
            if not self.agent or not self._current_project_name:
                return None
            workspace_path = FilmetoAgent._get_workspace_path(self.workspace)
            return f"{workspace_path}:{self._current_project_name}"

    # Create widget
    widget = MockAgentChatWidget(workspace)

    print("\n1. Switching to project_a...")
    project_a = MockProject("project_a")
    widget.on_project_switch(project_a)
    assert widget.get_current_project_name() == "project_a"
    assert widget.get_agent_instance_key() == f"{workspace.workspace_path}:project_a"
    print(f"   Active instances: {FilmetoAgent.list_instances()}")

    print("\n2. Switching to project_b...")
    project_b = MockProject("project_b")
    widget.on_project_switch(project_b)
    assert widget.get_current_project_name() == "project_b"
    assert widget.get_agent_instance_key() == f"{workspace.workspace_path}:project_b"
    print(f"   Active instances: {FilmetoAgent.list_instances()}")

    print("\n3. Switching back to project_a...")
    widget.on_project_switch(project_a)
    assert widget.get_current_project_name() == "project_a"
    # Should be the same instance as before
    assert widget.get_agent_instance_key() == f"{workspace.workspace_path}:project_a"
    print(f"   Active instances: {FilmetoAgent.list_instances()}")

    print("\n4. Verifying instance reuse...")
    instances = FilmetoAgent.list_instances()
    assert len(instances) == 2  # Should have exactly 2 instances
    assert f"{workspace.workspace_path}:project_a" in instances
    assert f"{workspace.workspace_path}:project_b" in instances
    print("   ✓ Correct number of instances maintained")

    print("\n5. Switching to same project (should be no-op)...")
    widget.on_project_switch(project_a)  # Same project
    assert widget.get_current_project_name() == "project_a"
    instances_after = FilmetoAgent.list_instances()
    assert len(instances_after) == 2  # Should still be 2
    print("   ✓ No new instance created")

    # Cleanup
    FilmetoAgent.clear_all_instances()

    print("\n" + "=" * 60)
    print("All project switching tests passed! ✓")
    print("=" * 60)


async def test_multiple_widgets_same_workspace():
    """Test multiple widgets sharing the same workspace."""
    print("\n" + "=" * 60)
    print("Testing Multiple Widgets with Same Workspace")
    print("=" * 60)

    FilmetoAgent.clear_all_instances()

    workspace = MockWorkspace("/tmp/filmeto_test_workspace_2")

    class SimpleWidget:
        def __init__(self, workspace, name):
            self.workspace = workspace
            self.name = name
            self._current_project_name = None
            self.agent = None

        def switch_to_project(self, project_name):
            from agent.filmeto_agent import FilmetoAgent

            self._current_project_name = project_name
            self.agent = FilmetoAgent.get_instance(
                workspace=self.workspace,
                project_name=project_name,
                model="gpt-4o-mini"
            )

    print("\n1. Creating two widgets...")
    widget1 = SimpleWidget(workspace, "Widget1")
    widget2 = SimpleWidget(workspace, "Widget2")

    print("\n2. Widget1 switches to project_x...")
    widget1.switch_to_project("project_x")

    print("\n3. Widget2 switches to project_x...")
    widget2.switch_to_project("project_x")

    print("\n4. Both widgets should share the same agent instance...")
    assert widget1.agent is widget2.agent
    print("   ✓ Widgets share the same agent instance")

    print("\n5. Widget2 switches to project_y...")
    widget2.switch_to_project("project_y")

    print("\n6. Widgets should now have different agent instances...")
    assert widget1.agent is not widget2.agent
    print("   ✓ Widgets have different agent instances")

    print(f"   Active instances: {FilmetoAgent.list_instances()}")
    assert len(FilmetoAgent.list_instances()) == 2

    # Cleanup
    FilmetoAgent.clear_all_instances()

    print("\n" + "=" * 60)
    print("All multi-widget tests passed! ✓")
    print("=" * 60)


async def main():
    """Run all tests."""
    await test_project_switching()
    await test_multiple_widgets_same_workspace()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓✓✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
