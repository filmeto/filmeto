"""
Test FilmetoAgent static instance management functionality.
"""
import asyncio
from agent.filmeto_agent import FilmetoAgent


class MockWorkspace:
    """Mock workspace for testing."""
    def __init__(self, path: str):
        self.workspace_path = path


class MockProject:
    """Mock project for testing."""
    def __init__(self, name: str):
        self.project_name = name


async def test_get_instance_creates_new_instance():
    """Test that get_instance creates a new instance when none exists."""
    print("Test 1: Creating new instance...")

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    workspace = MockWorkspace("/test/workspace")
    project_name = "test_project"

    agent = FilmetoAgent.get_instance(
        workspace=workspace,
        project_name=project_name,
        model="gpt-4o-mini"
    )

    assert agent is not None
    assert isinstance(agent, FilmetoAgent)
    assert FilmetoAgent.has_instance(workspace, project_name)

    print("✓ New instance created successfully")


async def test_get_instance_reuses_existing():
    """Test that get_instance reuses existing instance."""
    print("\nTest 2: Reusing existing instance...")

    workspace = MockWorkspace("/test/workspace2")
    project_name = "test_project2"

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    # Create first instance
    agent1 = FilmetoAgent.get_instance(
        workspace=workspace,
        project_name=project_name
    )

    # Get instance again - should be the same object
    agent2 = FilmetoAgent.get_instance(
        workspace=workspace,
        project_name=project_name
    )

    assert agent1 is agent2
    print("✓ Same instance reused successfully")


async def test_different_projects_different_instances():
    """Test that different projects get different instances."""
    print("\nTest 3: Different projects get different instances...")

    workspace = MockWorkspace("/test/workspace3")

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    agent1 = FilmetoAgent.get_instance(
        workspace=workspace,
        project_name="project_a"
    )

    agent2 = FilmetoAgent.get_instance(
        workspace=workspace,
        project_name="project_b"
    )

    assert agent1 is not agent2
    print("✓ Different projects have different instances")


async def test_different_workspaces_different_instances():
    """Test that different workspaces get different instances."""
    print("\nTest 4: Different workspaces get different instances...")

    workspace1 = MockWorkspace("/test/workspace4a")
    workspace2 = MockWorkspace("/test/workspace4b")

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    agent1 = FilmetoAgent.get_instance(
        workspace=workspace1,
        project_name="project_x"
    )

    agent2 = FilmetoAgent.get_instance(
        workspace=workspace2,
        project_name="project_x"
    )

    assert agent1 is not agent2
    print("✓ Different workspaces have different instances")


async def test_remove_instance():
    """Test removing an instance."""
    print("\nTest 5: Removing instance...")

    workspace = MockWorkspace("/test/workspace5")
    project_name = "test_project5"

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    # Create instance
    FilmetoAgent.get_instance(
        workspace=workspace,
        project_name=project_name
    )

    assert FilmetoAgent.has_instance(workspace, project_name)

    # Remove instance
    removed = FilmetoAgent.remove_instance(workspace, project_name)

    assert removed is True
    assert not FilmetoAgent.has_instance(workspace, project_name)
    print("✓ Instance removed successfully")


async def test_list_instances():
    """Test listing all instances."""
    print("\nTest 6: Listing instances...")

    # Clear any existing instances
    FilmetoAgent.clear_all_instances()

    workspace = MockWorkspace("/test/workspace6")

    # Create multiple instances
    FilmetoAgent.get_instance(workspace, "project_a")
    FilmetoAgent.get_instance(workspace, "project_b")
    FilmetoAgent.get_instance(workspace, "project_c")

    instances = FilmetoAgent.list_instances()

    assert len(instances) == 3
    assert f"{workspace.workspace_path}:project_a" in instances
    assert f"{workspace.workspace_path}:project_b" in instances
    assert f"{workspace.workspace_path}:project_c" in instances

    print(f"✓ Listed {len(instances)} instances: {instances}")


async def test_clear_all_instances():
    """Test clearing all instances."""
    print("\nTest 7: Clearing all instances...")

    workspace = MockWorkspace("/test/workspace7")

    # Create multiple instances
    FilmetoAgent.get_instance(workspace, "project_a")
    FilmetoAgent.get_instance(workspace, "project_b")

    assert len(FilmetoAgent.list_instances()) > 0

    # Clear all
    FilmetoAgent.clear_all_instances()

    assert len(FilmetoAgent.list_instances()) == 0
    print("✓ All instances cleared successfully")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing FilmetoAgent Static Instance Management")
    print("=" * 60)

    await test_get_instance_creates_new_instance()
    await test_get_instance_reuses_existing()
    await test_different_projects_different_instances()
    await test_different_workspaces_different_instances()
    await test_remove_instance()
    await test_list_instances()
    await test_clear_all_instances()

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

    # Clean up
    FilmetoAgent.clear_all_instances()


if __name__ == "__main__":
    asyncio.run(main())
