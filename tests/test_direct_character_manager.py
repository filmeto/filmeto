"""
Simple test to check if the background worker is working properly
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.data.workspace import Workspace


def test_character_manager_directly():
    """Test accessing actor manager directly without UI"""
    
    workspace_path = os.path.join(project_root, "workspace")
    demo_project_name = "demo"
    
    print("Testing direct access to actor manager...")
    
    # Initialize workspace with load_data=True
    workspace = Workspace(workspace_path, demo_project_name, load_data=True, defer_heavy_init=False)
    
    print("Getting project...")
    project = workspace.get_project()
    print(f"Project: {project is not None}")
    
    print("Getting actor manager...")
    character_manager = project.get_character_manager()
    print(f"Character manager: {character_manager is not None}")
    
    if character_manager:
        print("Listing characters...")
        try:
            characters = character_manager.list_characters()
            print(f"Number of characters: {len(characters)}")
            for char in characters[:3]:  # Print first 3
                print(f"  - {char.name}")
        except Exception as e:
            print(f"Error listing characters: {e}")
            logger.error(f"Error listing characters: {e}", exc_info=True)
    else:
        print("Character manager is None!")


if __name__ == "__main__":
    test_character_manager_directly()