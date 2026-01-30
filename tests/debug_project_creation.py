#!/usr/bin/env python
"""
Debug script to understand the project creation flow.
"""
import os
import tempfile
from app.data.workspace import Workspace
from app.data.project import Project

def debug_project_creation():
    """Debug the project creation process."""
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test 1: Direct project creation using ProjectManager
        print("\n=== Test 1: Creating project using ProjectManager ===")
        from app.data.project import ProjectManager
        project_manager = ProjectManager(temp_dir)
        project_name = "debug_project"
        
        print(f"Creating project: {project_name}")
        try:
            new_project = project_manager.create_project(project_name)
            print(f"Project created successfully!")
            print(f"Project path: {new_project.project_path}")
            
            # Check if directories exist
            expected_project_path = os.path.join(temp_dir, "projects", project_name)
            print(f"Expected project path exists: {os.path.exists(expected_project_path)}")
            print(f"Timeline dir exists: {os.path.exists(os.path.join(expected_project_path, 'timeline'))}")
            print(f"Project config exists: {os.path.exists(os.path.join(expected_project_path, 'project.yml'))}")
        except Exception as e:
            print(f"Error creating project: {e}")
            logger.error(f"Error creating project: {e}", exc_info=True)
        
        # Test 2: Workspace initialization
        print("\n=== Test 2: Workspace initialization ===")
        workspace_path = temp_dir
        project_name = "workspace_project"
        
        try:
            print(f"Initializing workspace with project: {project_name}")
            workspace = Workspace(workspace_path, project_name, load_data=True)
            print(f"Workspace initialized successfully!")
            print(f"Project path: {workspace.project_path}")
        except Exception as e:
            print(f"Error initializing workspace: {e}")
            logger.error(f"Error initializing workspace: {e}", exc_info=True)

if __name__ == "__main__":
    debug_project_creation()