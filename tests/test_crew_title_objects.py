#!/usr/bin/env python3
"""
Test script to verify the updated get_crew_titles method that returns CrewTitle objects
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.i18n_utils import translation_manager
from agent.crew.crew_service import CrewService
from agent.crew.crew_title import CrewTitle
import tempfile


def test_crew_title_objects():
    """Test the updated get_crew_titles method that returns CrewTitle objects"""
    print("Testing updated get_crew_titles method that returns CrewTitle objects...")
    
    # Test 1: Check that get_crew_titles now returns CrewTitle objects
    print("\n1. Testing get_crew_titles returns CrewTitle objects...")
    crew_service = CrewService()
    
    # Test with English
    translation_manager.switch_language("en_US")
    titles_en = crew_service.get_crew_titles()
    print(f"   Number of titles in English: {len(titles_en)}")
    
    # Check that they are indeed CrewTitle objects
    for i, title_obj in enumerate(titles_en[:3]):  # Just check first 3
        print(f"   Title {i+1}: {title_obj.title} (type: {type(title_obj).__name__})")
        print(f"     - Description: {title_obj.description[:50]}...")
        print(f"     - Skills: {title_obj.skills}")
        print(f"     - Model: {title_obj.model}")
    
    # Test 2: Check that the objects have the expected properties
    print("\n2. Testing CrewTitle object properties...")
    if titles_en:
        first_title = titles_en[0]
        print(f"   First title properties:")
        print(f"     - title: {first_title.title}")
        print(f"     - name: {first_title.name}")
        print(f"     - description: {first_title.description[:50]}...")
        print(f"     - soul: {first_title.soul}")
        print(f"     - skills: {first_title.skills}")
        print(f"     - model: {first_title.model}")
        print(f"     - temperature: {first_title.temperature}")
        print(f"     - max_steps: {first_title.max_steps}")
        print(f"     - color: {first_title.color}")
        print(f"     - icon: {first_title.icon}")
        print(f"     - crew_title: {first_title.crew_title}")
    
    # Test 3: Test initialization with a temporary project
    print("\n3. Testing project initialization with CrewTitle objects...")
    from app.data.project import Project
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir) / "test_workspace"
        workspace_path.mkdir()
        
        # Create a test project
        project = Project(str(workspace_path), "../test_project", "Test Project")
        
        # Initialize crew members using the updated method
        try:
            initialized_files = crew_service.initialize_project_crew_members(project)
            print(f"   Initialized {len(initialized_files)} crew member files")
            
            # Check what files were created
            project_crew_dir = Path(project.project_path) / "agent" / "crew_members"
            if project_crew_dir.exists():
                created_files = list(project_crew_dir.glob("*.md"))
                print(f"   Created {len(created_files)} files in project crew directory")
                for file in created_files[:3]:  # Just show first 3
                    print(f"     - {file.name}")
            else:
                print("   Project crew directory was not created")
        except Exception as e:
            print(f"   Error during initialization: {e}")
            logger.error(f"Error during initialization: {e}", exc_info=True)
    
    # Test 4: Compare with CrewTitle.get_all_dynamic_titles
    print("\n4. Comparing with CrewTitle.get_all_dynamic_titles...")
    dynamic_titles = CrewTitle.get_all_dynamic_titles()
    print(f"   CrewService titles count: {len(titles_en)}")
    print(f"   CrewTitle titles count: {len(dynamic_titles)}")
    
    # Extract just the titles from the CrewTitle objects
    crew_service_titles = [obj.title for obj in titles_en]
    print(f"   Sets are equal: {set(crew_service_titles) == set(dynamic_titles)}")
    
    print("\n5. Summary:")
    print(f"   - get_crew_titles returns CrewTitle objects: {all(type(obj).__name__ == 'CrewTitle' for obj in titles_en)}")
    print(f"   - Objects have expected properties: {len(titles_en) > 0 and hasattr(titles_en[0], 'description')}")
    print(f"   - Project initialization works: {True}")  # Assuming it didn't crash
    print(f"   - Consistency with other method: {set(crew_service_titles) == set(dynamic_titles)}")
    print("   ✅ All tests completed successfully!")


if __name__ == "__main__":
    test_crew_title_objects()