"""
Final test to verify the CharacterPanel loading fix
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from app.data.workspace import Workspace
from app.ui.panels.actor.actor_panel import ActorPanel


def test_character_panel_loading_fix():
    """Test that the CharacterPanel loading fix works properly"""
    
    # Create Qt application
    app = QApplication([])
    
    workspace_path = os.path.join(project_root, "workspace")
    demo_project_name = "demo"
    
    print("Testing CharacterPanel loading with the fix...")
    
    # Initialize workspace with load_data=True (should load actor data immediately due to our fix)
    workspace = Workspace(workspace_path, demo_project_name, load_data=True, defer_heavy_init=False)
    
    print("Creating CharacterPanel...")
    
    # Create CharacterPanel
    panel = ActorPanel(workspace)
    
    print(f"Initial state - _data_loaded: {panel._data_loaded}")
    print(f"Initial state - _is_active: {panel._is_active}")
    print(f"Initial state - character_manager: {panel.character_manager}")
    
    # Simulate activation (this is the normal flow)
    print("\nSimulating panel activation...")
    panel.on_activated()
    
    print(f"After activation - _data_loaded: {panel._data_loaded}")
    print(f"After activation - _is_active: {panel._is_active}")
    print(f"After activation - character_manager: {panel.character_manager}")
    
    # Wait a bit for async operations to complete
    import time
    start_time = time.time()
    timeout = 5  # 5 seconds timeout
    
    print("\nWaiting for actor manager to load...")
    while time.time() - start_time < timeout:
        app.processEvents()
        time.sleep(0.1)
        if panel.character_manager is not None:
            print("✓ Character manager loaded!")
            break
    else:
        print("⚠ Character manager still None after timeout")
    
    print(f"Final state - character_manager: {panel.character_manager is not None}")
    
    if panel.character_manager:
        print("✓ Character manager successfully loaded!")
        # Try to list characters
        try:
            chars = panel.character_manager.list_characters()
            print(f"✓ Number of characters loaded: {len(chars)}")
            print("✓ Sample actor names:")
            for i, char in enumerate(chars[:3]):  # Print first 3 characters
                print(f"  - {char.name}")
                
            # Verify that we have at least the expected characters
            expected_chars = ["wegweg", "fuli"]  # Two known characters from the demo
            found_expected = [name for name in expected_chars if any(c.name == name for c in chars)]
            print(f"✓ Found expected characters: {found_expected}")
            
            if len(found_expected) == len(expected_chars):
                print("✅ All expected characters found - CharacterPanel loading fix works!")
            else:
                print("⚠ Some expected characters not found")
                
        except Exception as e:
            print(f"✗ Error listing characters: {e}")
            logger.error(f"Error listing characters: {e}", exc_info=True)
    else:
        print("✗ Character manager is still None - loading failed!")
    
    print("\nTest completed.")


if __name__ == "__main__":
    test_character_panel_loading_fix()