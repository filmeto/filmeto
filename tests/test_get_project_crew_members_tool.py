"""
Test script for the updated GetProjectCrewMembersTool
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tool.system.get_project_crew_members import GetProjectCrewMembersTool


def test_get_project_crew_members_tool():
    """Test the GetProjectCrewMembersTool with a mock project"""
    print("Testing GetProjectCrewMembersTool...")
    
    # Create a mock project object
    class MockProject:
        def __init__(self):
            self.project_name = "TestProject"
            self.project_path = "/tmp/test_project"
    
    # Create a mock workspace object
    class MockWorkspace:
        def __init__(self):
            self.workspace_path = "/tmp/test_workspace"
    
    # Create the tool
    tool = GetProjectCrewMembersTool()
    
    # Create a mock context with project and workspace
    mock_project = MockProject()
    mock_workspace = MockWorkspace()
    context = {
        'project': mock_project,
        'workspace': mock_workspace
    }
    
    # Execute the tool
    try:
        result = tool.execute({}, context)
        print(f"Tool executed successfully. Found {len(result)} crew members.")
        
        for member in result:
            print(f"  - Name: {member['name']}, Role: {member['role']}, Skills: {member['skills']}")
        
        return result
    except Exception as e:
        print(f"Error executing tool: {e}")
        logger.error(f"Error executing tool: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    print("Running GetProjectCrewMembersTool test...\n")
    result = test_get_project_crew_members_tool()
    
    if result is not None:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed!")
        sys.exit(1)